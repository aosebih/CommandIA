
import uuid
import json
import re
from typing import Optional, Dict, Any, List

from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL
from schemas import (
    DeliveryType,
    OrderExtractionData,
    OrderExtractionResponse,
    OrderStatus,
)
from system_prompt import SYSTEM_PROMPT_V1
from wilayas import get_wilaya_code, get_wilaya_name


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
        self.failed_data_attempts = 0
        self.language = "franco_arabic"
        self.product_context: Dict[str, Any] = {}
        self.user_message_history: List[str] = []
        self.assistant_message_history: List[str] = []
        self.escalated = False
        self.order_status = OrderStatus.PENDING_CONFIRMATION.value


class AIBrain:
   
    
    def __init__(self, api_key: Optional[str] = None, model: str = GEMINI_MODEL):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Set it in environment variables.")
        
       
        self.client = genai.Client(api_key=self.api_key)
        self.model = model
        self.system_prompt = SYSTEM_PROMPT_V1
    
    def _detect_language(self, message: str) -> str:
        
        # Count Arabic characters (Darija in Arabic script)
        arabic_chars = sum(1 for c in message if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F')
        total_chars = len(message.strip())
        
        if total_chars == 0:
            return "franco_arabic"
        
        if arabic_chars / total_chars > 0.3:
            return "darija"
        
        franco_patterns = ['3', '7', '9', '2', '5', 'kh', 'ch', 'gh', 'bch', 't9', 'kifach', 'wach', 'rani', '3tini', 'bghit']
        message_lower = message.lower()
        if any(p in message_lower for p in franco_patterns):
            return "franco_arabic"
        
        french_keywords = ['bonjour', 'merci', 'prix', 'livraison', 'commande', 'acheter', 'veux']
        if any(k in message_lower for k in french_keywords):
            return "french"

        return "english"
    
    def _update_missing_fields(self, extracted: Dict[str, Any]) -> List[str]:
        missing = []
        required = [
            "customer_name",
            "phone_number",
            "wilaya_code",
            "delivery_type",
            "address",
        ]
        for field in required:
            value = extracted.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
            elif field == "wilaya_code" and get_wilaya_name(value) is None:
                missing.append(field)
        return missing
    
    def _create_fallback_order(self, state: ConversationState) -> Dict[str, Any]:
        collected = state.collected_fields
        return OrderExtractionData(
            customer_name=collected.get("customer_name"),
            phone_number=collected.get("phone_number"),
            wilaya_code=collected.get("wilaya_code"),
            delivery_type=collected.get("delivery_type"),
            address=collected.get("address"),
            total_price_da=state.product_context.get("total_price_da"),
            order_status=(
                OrderStatus.REQUIRES_HUMAN
                if state.escalated
                else OrderStatus.PENDING_CONFIRMATION
            ),
        ).model_dump(mode="json")

    def _to_legacy_order(
        self,
        state: ConversationState,
        extracted_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        items = extracted_data.get("order_items") or []
        first_item = items[0] if items else {}
        product_context = state.product_context
        fallback_total = product_context.get("total_price_da")
        return {
            "order_id": str(uuid.uuid4()),
            "customer_name": extracted_data.get("customer_name") or "",
            "phone_number": extracted_data.get("phone_number") or "",
            "wilaya": get_wilaya_name(extracted_data.get("wilaya_code")) or "",
            "delivery_type": extracted_data.get("delivery_type") or DeliveryType.HOME.value,
            "address": extracted_data.get("address") or "",
            "product_details": {
                "item_id": first_item.get("product_name")
                or product_context.get("item_id", "unknown"),
                "quantity": first_item.get("quantity")
                or product_context.get("quantity", 1),
                "size_color": first_item.get("size_color")
                or product_context.get("size_color", ""),
            },
            "total_price_da": extracted_data.get("total_price_da")
            if extracted_data.get("total_price_da") is not None
            else fallback_total,
            "order_status": extracted_data.get(
                "order_status", OrderStatus.PENDING_CONFIRMATION.value
            ),
        }

    @staticmethod
    def _is_explicit_confirmation(message: str) -> bool:
        return bool(
            re.search(
                r"\b(yes|yeah|yep|confirm|confirmed|oui|d'accord|daccord|"
                r"نعم|ايه|إيه|نأكد|nconfirmi|n3am)\b",
                message.casefold(),
            )
        )
    
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
        
        Returns a canonical extraction plus compatibility keys used by the CLI.
        """
        if conversation_state is None:
            conversation_state = ConversationState()
        
        if product_context:
            conversation_state.product_context.update(product_context)
        
        # Detect language
        detected_lang = self._detect_language(user_message)
        conversation_state.language = detected_lang
        conversation_state.attempts += 1
        
        # Build conversation context
        history_context = self._build_history(conversation_state)
        conversation_state.user_message_history.append(user_message)
        
        # Prepare prompt with full context
        full_prompt = f"""{self.system_prompt}

## Current Conversation State
- Conversation ID: {conversation_state.conversation_id}
- State: {conversation_state.state}
- Detected Language: {conversation_state.language}
- Failed data-collection attempts: {conversation_state.failed_data_attempts}
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
If escalation is needed (frustrated, bulk pricing request, or 3 failed data-collection attempts), set order_status to "REQUIRES_HUMAN".
Only set order_status to "CONFIRMED" if ALL 5 Sacred Fields are valid AND user explicitly confirms.

Return only the JSON object matching this exact shape:
{{"reply_to_customer": "message", "extracted_data": {{"customer_name": null, "phone_number": null, "wilaya_code": null, "delivery_type": null, "address": null, "order_items": [], "subtotal_da": null, "shipping_fee_da": null, "total_price_da": null, "order_status": "PENDING_CONFIRMATION"}}}}

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
                    response_mime_type="application/json",
                    response_schema=OrderExtractionResponse,
                ),
            )
            
            response_text_raw = response.text if response.text else ""
            
            # Parse JSON response
            parsed = self._parse_ai_response(response_text_raw)
            extraction = OrderExtractionResponse.model_validate(parsed)
            response_text = extraction.reply_to_customer
            order_data = extraction.extracted_data.model_dump(mode="json")
            
            # Validate and update conversation state
            self._update_conversation_state(conversation_state, order_data, user_message, response_text)
            order_data["order_status"] = conversation_state.order_status
            
            return {
                "reply_to_customer": response_text,
                "extracted_data": order_data,
                "response_text": response_text,
                "order_data": self._to_legacy_order(conversation_state, order_data),
                "conversation_id": conversation_state.conversation_id,
                "state": conversation_state.state,
                "missing_fields": conversation_state.missing_fields,
                "collected_fields": conversation_state.collected_fields,
                "escalated": conversation_state.escalated,
                "language": conversation_state.language,
            }
            
        except Exception:
            fallback_data = self._create_fallback_order(conversation_state)
            fallback_text = self._get_fallback_response(conversation_state.language)
            conversation_state.assistant_message_history.append(fallback_text)
            
            return {
                "reply_to_customer": fallback_text,
                "extracted_data": fallback_data,
                "response_text": fallback_text,
                "order_data": self._to_legacy_order(conversation_state, fallback_data),
                "conversation_id": conversation_state.conversation_id,
                "state": conversation_state.state,
                "missing_fields": conversation_state.missing_fields,
                "collected_fields": conversation_state.collected_fields,
                "escalated": conversation_state.escalated,
                "error": "AI response could not be generated or validated",
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
        Parse a JSON response, accepting an optional Markdown code fence.
        """
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.find("\n")
            closing_fence = cleaned.rfind("```")
            if first_newline < 0 or closing_fence <= first_newline:
                raise ValueError("Gemini returned an incomplete JSON code fence")
            cleaned = cleaned[first_newline + 1:closing_fence].strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini response must be a JSON object")
        return parsed
    
    def _update_conversation_state(
        self,
        state: ConversationState,
        order_data: Dict[str, Any],
        user_msg: str,
        assistant_msg: str,
    ):
        """Update conversation state based on extracted data."""
        state.assistant_message_history.append(assistant_msg)
        previous_state = state.state
        previous_fields = dict(state.collected_fields)
        
        # Update collected fields
        if order_data:
            for field in (
                "customer_name",
                "phone_number",
                "wilaya_code",
                "delivery_type",
                "address",
            ):
                val = order_data.get(field)
                if val is not None and (not isinstance(val, str) or val.strip()):
                    state.collected_fields[field] = val
            
            if order_data.get("order_items"):
                state.product_context["order_items"] = order_data["order_items"]
            for price_field in ("subtotal_da", "shipping_fee_da", "total_price_da"):
                if order_data.get(price_field) is not None:
                    state.product_context[price_field] = order_data[price_field]
        
        # Update missing fields
        state.missing_fields = self._update_missing_fields(state.collected_fields)

        added_valid_field = any(
            state.collected_fields.get(field) != previous_fields.get(field)
            for field in state.collected_fields
        )
        if previous_state in {"ORDER_INTENT", "DATA_COLLECTION"}:
            if added_valid_field:
                state.failed_data_attempts = 0
            else:
                state.failed_data_attempts += 1

        if order_data.get("order_status") == OrderStatus.REQUIRES_HUMAN.value:
            state.escalated = True

        if (
            order_data.get("order_status") == OrderStatus.CONFIRMED.value
            and not state.missing_fields
            and self._is_explicit_confirmation(user_msg)
        ):
            state.order_status = OrderStatus.CONFIRMED.value
        elif state.escalated or state.failed_data_attempts >= 3:
            state.order_status = OrderStatus.REQUIRES_HUMAN.value
            state.escalated = True
        else:
            state.order_status = OrderStatus.PENDING_CONFIRMATION.value
        
        # Update state machine
        if state.escalated:
            state.state = "ESCALATION"
        elif not state.missing_fields:
            # All fields collected
            state.state = "CONFIRMATION"
        elif state.state == "CONFIRMATION":
            state.state = "DATA_COLLECTION"
        elif "buy" in user_msg.lower() or "nchri" in user_msg.lower() or "acheter" in user_msg.lower() or "3tini" in user_msg.lower():
            if state.state == "INQUIRY":
                state.state = "ORDER_INTENT"
        elif state.state in ["ORDER_INTENT", "INQUIRY"] and len(state.collected_fields) > 0:
            state.state = "DATA_COLLECTION"
        elif len(state.collected_fields) > 0 or len(state.missing_fields) < 5:
            if state.state not in ["CONFIRMATION", "ESCALATION"]:
                state.state = "DATA_COLLECTION"
    
    def _get_fallback_response(self, language: str) -> str:
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
