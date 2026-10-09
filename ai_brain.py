
import uuid
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from google import genai
from google.genai import types
from pydantic import ValidationError

from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_RETRIES
from schemas import OrderExtractionResponse, Order, OrderStatus, DeliveryType, OrderItem
from system_prompt import SYSTEM_PROMPT_V1
from wilayas import ALGERIAN_WILAYAS_LIST, is_valid_wilaya, get_wilaya_code, get_wilaya_name


class ConversationState:
    
    
    def __init__(self, conversation_id: Optional[str] = None):
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.state = "INQUIRY"  # INQUIRY, ORDER_INTENT, DATA_COLLECTION, CONFIRMATION
        self.collected_fields: Dict[str, Any] = {}
        self.missing_fields: List[str] = [
            "customer_name",
            "phone_number", 
            "wilaya_code",
            "delivery_type",
            "address"
        ]
        self.attempts = 0
        self.language = "franco_arabic"  # default
        self.product_context: Dict[str, Any] = {}
        self.user_message_history: List[str] = []
        self.assistant_message_history: List[str] = []
        self.escalated = False


class AIBrain:
    """
    AI Brain for CommandIA using Gemini API.
    Extracts structured order data with Pydantic validation.
    No fine-tuning - uses prompt engineering only as per requirements.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = GEMINI_MODEL):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Set it in environment variables.")
        
        # Initialize Gemini client
        self.client = genai.Client(api_key=self.api_key)
        self.model = model
        self.system_prompt = SYSTEM_PROMPT_V1
        
        # # Define response schema for structured output using Pydantic
        # self.response_schema = types.Schema(
        #     type=types.Type.OBJECT,
        #     properties={
        #         "order_id": types.Schema(type=types.Type.STRING),
        #         "customer_name": types.Schema(type=types.Type.STRING),
        #         "phone_number": types.Schema(type=types.Type.STRING),
        #         "wilaya": types.Schema(type=types.Type.STRING),
        #         "delivery_type": types.Schema(type=types.Type.STRING, enum=["HOME", "DESK"]),
        #         "address": types.Schema(type=types.Type.STRING),
        #         "product_details": types.Schema(
        #             type=types.Type.OBJECT,
        #             properties={
        #                 "item_id": types.Schema(type=types.Type.STRING),
        #                 "quantity": types.Schema(type=types.Type.INTEGER),
        #                 "size_color": types.Schema(type=types.Type.STRING),
        #             },
        #             required=["item_id", "quantity", "size_color"],
        #         ),
        #         "total_price_da": types.Schema(type=types.Type.NUMBER),
        #         "order_status": types.Schema(
        #             type=types.Type.STRING,
        #             enum=["PENDING_CONFIRMATION", "CONFIRMED", "REQUIRES_HUMAN"],
        #         ),
        #     },
        #     required=[
        #         "order_id",
        #         "customer_name",
        #         "phone_number",
        #         "wilaya",
        #         "delivery_type",
        #         "address",
        #         "product_details",
        #         "total_price_da",
        #         "order_status",
        #     ],
        # )
    
    def _detect_language(self, message: str) -> str:
        """
        Detect language/dialect from user message.
        Returns: darija, franco_arabic, french, or english
        """
        # Count Arabic characters (Darija in Arabic script)
        arabic_chars = sum(1 for c in message if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F')
        total_chars = len(message.strip())
        
        if total_chars == 0:
            return "franco_arabic"
        
        # If significant Arabic script, likely Darija
        if arabic_chars / total_chars > 0.3:
            return "darija"
        
        # Check for Franco-Arabic patterns (mix of Latin + numbers like 3, 7, 9, 2, 5)
        franco_patterns = ['3', '7', '9', '2', '5', 'kh', 'ch', 'gh', 'bch', 't9', 'kifach', 'wach', 'rani', '3tini', 'bghit']
        message_lower = message.lower()
        if any(p in message_lower for p in franco_patterns):
            return "franco_arabic"
        
        # French vs English - simple heuristic
        french_keywords = ['bonjour', 'merci', 'prix', 'livraison', 'commande', 'acheter', 'veux']
        if any(k in message_lower for k in french_keywords):
            return "french"
        
        # Default to English if mostly ASCII and no clear patterns
        return "english"
    
    def _update_missing_fields(self, extracted: Dict[str, Any]) -> List[str]:
        """Update list of missing fields based on extraction."""
        missing = []
        required = ["customer_name", "phone_number", "wilaya_code", "delivery_type", "address"]
        for field in required:
            value = extracted.get(field)
            if not value or (isinstance(value, str) and value.strip() == ""):
                missing.append(field)
            elif field == "wilaya_code":
                if not isinstance(value, int) or not (1 <= value <= 69):
                    missing.append(field)
            elif field == "phone_number":
                try:
                    cleaned = ''.join(filter(str.isdigit, str(value)))
                    if not (cleaned.startswith(('05', '06', '07')) and len(cleaned) == 10):
                        missing.append(field)
                except:
                    missing.append(field)
        return missing
    
    def _create_fallback_order(self, state: ConversationState) -> Dict[str, Any]:
        """Create a fallback order structure with collected data."""
        collected = state.collected_fields
        order_items = []
        if state.product_context.get("order_items"):
            order_items = state.product_context.get("order_items")
        else:
            # Keep legacy product details if present
            pd = state.product_context
            if pd.get("product_name") or pd.get("item_id"):
                order_items = [{
                    "product_name": pd.get("product_name") or pd.get("item_id", "unknown"),
                    "quantity": pd.get("quantity", 1),
                    "size_color": pd.get("size_color"),
                    "unit_price_da": pd.get("unit_price_da"),
                }]
        
        # Compute totals
        subtotal = 0.0
        for item in order_items:
            qty = int(item.get("quantity", 0)) if item.get("quantity") else 0
            price = float(item.get("unit_price_da", 0)) if item.get("unit_price_da") is not None else 0
            subtotal += qty * price
        shipping = float(state.product_context.get("shipping_fee_da", 0)) if state.product_context.get("shipping_fee_da") is not None else 0
        total = subtotal + shipping
        
        return {
            "reply_to_customer": "",
            "extracted_data": {
                "customer_name": collected.get("customer_name"),
                "phone_number": collected.get("phone_number"),
                "wilaya_code": collected.get("wilaya_code"),
                "delivery_type": collected.get("delivery_type"),
                "address": collected.get("address"),
                "order_items": order_items,
                "subtotal_da": subtotal,
                "shipping_fee_da": shipping,
                "total_price_da": total,
                "order_status": OrderStatus.REQUIRES_HUMAN.value if state.escalated else OrderStatus.PENDING_CONFIRMATION.value,
            }
        }
    
    def process_message(
        self,
        user_message: str,
        conversation_state: Optional[ConversationState] = None,
        product_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process user message and return AI response with extracted order data.
        
        Args:
            user_message: User's message in any supported dialect
            conversation_state: Existing conversation state (for multi-turn)
            product_context: Context about product (price, item_id, etc.)
        
        Returns:
            Dict containing response_text, order_data, state_info
        """
        if conversation_state is None:
            conversation_state = ConversationState()
        
        if product_context:
            conversation_state.product_context.update(product_context)
        
        # Detect language
        detected_lang = self._detect_language(user_message)
        conversation_state.language = detected_lang
        conversation_state.user_message_history.append(user_message)
        conversation_state.attempts += 1
        
        # Build conversation context
        history_context = self._build_history(conversation_state)
        
        # Prepare prompt with full context
        full_prompt = f"""{self.system_prompt}

## Current Conversation State
- Conversation ID: {conversation_state.conversation_id}
- State: {conversation_state.state}
- Detected Language: {conversation_state.language}
- Attempts: {conversation_state.attempts}
- Escalated: {conversation_state.escalated}

## Collected Fields So Far
{json.dumps(conversation_state.collected_fields, indent=2, ensure_ascii=False)}

## Missing Fields
{json.dumps(conversation_state.missing_fields, indent=2, ensure_ascii=False)}

## Product Context
{json.dumps(conversation_state.product_context, indent=2, ensure_ascii=False)}

## Conversation History
{history_context}

## User Message (Latest)
{user_message}

## Instructions
Respond with a helpful message in the user's language ({detected_lang}), AND extract any order information into valid JSON matching the exact schema.
If escalation is needed (frustrated, bulk pricing request, >3 failed attempts), set order_status to "REQUIRES_HUMAN".
Only set order_status to "CONFIRMED" if ALL 5 Sacred Fields are valid AND user explicitly confirms.

Return your response as JSON with two keys:
1. "response_text" - Natural language response to user (in their language)
2. "order_data" - Extracted order data matching schema (fill what's known, empty strings if unknown)

Be precise and follow all guardrails.
"""
        
        try:
            # Call Gemini API with structured thinking
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temp for more consistent extraction
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=2048,
                    # response_mime_type="application/json",
                    # response_schema=self.response_schema,
                ),
            )
            
            response_text_raw = response.text if response.text else ""
            
            # Parse JSON response
            parsed = self._parse_ai_response(response_text_raw)
            response_text = parsed.get("reply_to_customer") or parsed.get("response_text") or "Je n'ai pas compris. Peux-tu répéter ?"
            extracted = parsed.get("extracted_data", parsed.get("order_data", {}))
            order_data = {
                "reply_to_customer": response_text,
                "extracted_data": extracted
            }
            
            # Validate and update conversation state
            self._update_conversation_state(conversation_state, order_data, user_message, response_text)
            
            return {
                "response_text": response_text,
                "order_data": order_data,
                "conversation_id": conversation_state.conversation_id,
                "state": conversation_state.state,
                "missing_fields": conversation_state.missing_fields,
                "collected_fields": conversation_state.collected_fields,
                "escalated": conversation_state.escalated,
                "language": conversation_state.language,
            }
            
        except Exception as e:
            # Fallback on error
            conversation_state.attempts += 0  # don't count failed API call as extraction attempt?
            fallback_order = self._create_fallback_order(conversation_state)
            fallback_text = self._get_fallback_response(conversation_state.language, str(e))
            conversation_state.assistant_message_history.append(fallback_text)
            
            return {
                "response_text": fallback_text,
                "order_data": fallback_order,
                "conversation_id": conversation_state.conversation_id,
                "state": conversation_state.state,
                "missing_fields": conversation_state.missing_fields,
                "collected_fields": conversation_state.collected_fields,
                "escalated": conversation_state.escalated,
                "error": str(e),
            }
    
    def _build_history(self, state: ConversationState) -> str:
        """Build conversation history for context."""
        lines = []
        # Build recent history (last 10 exchanges)
        max_exchanges = min(5, len(state.user_message_history))
        for i in range(-max_exchanges, 0):
            if i < -len(state.user_message_history):
                break
            user_msg = state.user_message_history[i] if abs(i) <= len(state.user_message_history) else ""
            asst_msg = state.assistant_message_history[i] if abs(i) <= len(state.assistant_message_history) else ""
            if user_msg:
                lines.append(f"User: {user_msg}")
            if asst_msg:
                lines.append(f"Assistant: {asst_msg}")
        return "\n".join(lines) if lines else "No previous exchanges."
    
    def _parse_ai_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse AI response. Try to extract JSON from markdown blocks or raw JSON.
        """
        try:
            # Try to find JSON in markdown code blocks
            if "```json" in raw_response:
                start = raw_response.find("```json") + 7
                end = raw_response.find("```", start)
                if end != -1:
                    json_str = raw_response[start:end].strip()
                    return json.loads(json_str)
            elif "```" in raw_response:
                # Generic code block
                start = raw_response.find("```") + 3
                # Skip language if present
                nl = raw_response.find("\n", start)
                if nl != -1 and raw_response[start:nl].strip() == "":
                    start = nl + 1
                end = raw_response.find("```", start)
                if end != -1:
                    json_str = raw_response[start:end].strip()
                    # Try to parse - might be JSON
                    try:
                        return json.loads(json_str)
                    except:
                        pass
            
            # Try to parse as raw JSON
            return json.loads(raw_response.strip())
            
        except json.JSONDecodeError:
            # Fallback: try to extract from text
            # Look for response_text and order_data patterns
            result = {
                "response_text": raw_response.strip(),
                "order_data": {}
            }
            return result
    
    def _update_conversation_state(
        self,
        state: ConversationState,
        order_data: Dict[str, Any],
        user_msg: str,
        assistant_msg: str,
    ):
        """Update conversation state based on extracted data."""
        state.assistant_message_history.append(assistant_msg)
        
        # Update collected fields
        if order_data:
            extracted = order_data.get("extracted_data", order_data)
            # Extract fields
            for field in ["customer_name", "phone_number", "wilaya_code", "wilaya", "delivery_type", "address"]:
                val = extracted.get(field)
                if val is not None and str(val).strip():
                    state.collected_fields[field] = val
            
            # Normalize wilaya_code from wilaya name if needed
            if state.collected_fields.get("wilaya_code") is None and state.collected_fields.get("wilaya"):
                code = get_wilaya_code(state.collected_fields.get("wilaya"))
                if code:
                    state.collected_fields["wilaya_code"] = code
            
            # Product details/items
            if extracted.get("order_items"):
                state.product_context["order_items"] = extracted["order_items"]
            elif extracted.get("product_details"):
                pd = extracted.get("product_details", {})
                state.product_context.update(pd)
            for key in ["subtotal_da", "shipping_fee_da", "total_price_da"]:
                if key in extracted and extracted[key] is not None:
                    state.product_context[key] = extracted[key]
            status = extracted.get("order_status") or order_data.get("order_status")
            if status == "REQUIRES_HUMAN":
                state.escalated = True
                state.state = "ESCALATION"
            elif status == "CONFIRMED":
                state.state = "CONFIRMATION"
        
        # Update missing fields
        state.missing_fields = self._update_missing_fields(state.collected_fields)
        
        # Update state machine
        if state.escalated:
            state.state = "ESCALATION"
        elif len(state.missing_fields) == 0 and len(state.collected_fields) == 5:
            # All fields collected
            if state.state != "CONFIRMATION":
                state.state = "CONFIRMATION"
        elif "buy" in user_msg.lower() or "nchri" in user_msg.lower() or "acheter" in user_msg.lower() or "3tini" in user_msg.lower():
            if state.state == "INQUIRY":
                state.state = "ORDER_INTENT"
        elif state.state in ["ORDER_INTENT", "INQUIRY"] and len(state.collected_fields) > 0:
            state.state = "DATA_COLLECTION"
        elif len(state.collected_fields) > 0 or len(state.missing_fields) < 5:
            if state.state not in ["CONFIRMATION", "ESCALATION"]:
                state.state = "DATA_COLLECTION"
    
    def _get_fallback_response(self, language: str, error: str) -> str:
        """Get fallback response in appropriate language."""
        fallbacks = {
            "french": "Désolé, une erreur s'est produite. Peux-tu reformuler ta demande ?",
            "english": "Sorry, an error occurred. Could you please rephrase your request?",
            "darija": "سامحني، وقع خطأ. تقدر تعاود الطلب بلطف؟",
            "franco_arabic": "Smahni, 3adit erreur. T9ad tchufit message ta3i w ta3awed?",
        }
        return fallbacks.get(language, fallbacks["franco_arabic"])
    
    def reset_conversation(self, conversation_id: Optional[str] = None) -> ConversationState:
        """Reset conversation state."""
        return ConversationState(conversation_id=conversation_id)


# Helper function to test extraction
def create_test_conversation():
    """Create a sample conversation for testing."""
    brain = AIBrain()
    state = ConversationState()
    return brain, state
