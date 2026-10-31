
import uuid
import json
import logging
import re
import time
import unicodedata
from typing import Optional, Dict, Any, List

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_MODEL_FALLBACKS,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
)
from schemas import (
    DeliveryType,
    OrderExtractionData,
    OrderExtractionResponse,
    OrderStatus,
    normalize_algerian_phone,
)
from system_prompt import SYSTEM_PROMPT_V1
from wilayas import get_wilaya_code, get_wilaya_name

logger = logging.getLogger("commandia.ai_brain")

# HTTP-ish codes worth retrying: rate limits and temporary upstream failures.
TRANSIENT_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}

# --- Language detection lexicon -------------------------------------------------
# Franco-Arabic is Algerian Darija written in Latin script. Its markers are
# distinctive enough to be matched on word boundaries without false positives.
FRANCO_ARABIC_MARKERS = (
    "3afak", "3afakom", "3andkom", "3andkoum", "3andna", "3andek", "3jbat", "3la",
    "3lik", "3lih", "3nin", "3tina", "3tini", "3tawa", "3te", "7ala", "7awl", "7el",
    "9dek", "9ndek", "9oul", "9der", "ahlan", "b9a", "b9der", "bch", "bchhal",
    "bchh", "bghit", "bghitk", "bghitna", "bqa", "b9der", "bzaf", "bzid", "chhal",
    "chhalna", "chri", "chwiya", "daba", "daba3", "esmi", "fhamt", "fhamtach", "ghib",
    "hach", "hadi", "hal", "hna", "howa", "ismi", "kifach", "kifak", "kifakna",
    "kifakom", "kifak", "kona", "kont", "kontom", "labas", "m3a", "m3ak", "m3li",
    "m3lik", "machi", "marhaba", "mes", "mch", "mchhol", "mrad", "mrhaba", "mrabet",
    "msa", "mzn", "n9der", "nchri", "nchrih", "najem", "nas", "ndir", "njem",
    "rahma", "rani", "rannikh", "safi", "salam", "slama", "smahli", "sme7li",
    "t9der", "t9derk", "ta3i", "ta3", "tekber", "telefon", "tel", "thmen", "w7id",
    "wach", "wa5", "wllah", "y7it", "ya3tik", "ya3tini", "ye3tik", "zid", "numero",
)
FRANCO_ARABIC_PHRASES = (
    "ana men", "men had", "bch nchri", "chhal thmen", "bchhal", "kifach hna",
    "wach kifach", "nchri had", "bghit nchri", "kifak hna", "m3a slama",
    "salam", "labas", "mrabet", "ahlan", "tekber", "3afak", "ya3tik", "msa",
    "mrhba", "chhal", "bchhal", "tchri", "kifachk",
)
# A word starting with 3, 7 or 9 followed by letters is a strong Darija-latin
# signal ("3andkom", "9ndek", "7awl"). Prices such as "3500" are excluded
# because they contain no letter.
FRANCO_ARABIC_DIGIT_PATTERN = re.compile(r"\b[379][a-z]{2,}\b")

FRENCH_MARKERS = (
    "adresse", "algerie", "argent", "bureau", "cher", "chere", "commande",
    "commander", "combien", "couleur", "disponible", "domicile", "interesse",
    "livraison", "livrer", "livrez", "marque", "merci", "modele", "paiement",
    "pointure", "prix", "qualite", "reference", "salut", "santec", "sizes",
    "taille", "tapis", "telephone", "wilaya", "wilti",
)
ENGLISH_MARKERS = (
    "available", "can i", "colour", "delivery", "do you have", "evening",
    "good", "hello", "hey", "home delivery", "how much", "interested", "looking",
    "morning", "need", "order", "please", "price", "ship", "shipping", "size",
    "stock", "thank", "want", "buy",
)

# Unambiguous purchase expressions, used only when the model does not report a
# conversational state. Kept deliberately narrow: a false positive would push a
# price question into the ordering flow.
ORDER_INTENT_MARKERS = (
    "nchri", "3tini", "3tina", "acheter", "achete", "commander", "commande",
    "i want to buy", "i want to order", "i want to purchase", "i would like to order",
    "i'd like to order", "let me order", "buy it",
)


def _strip_accents(text: str) -> str:
    """Remove diacritics so "achete" also matches "achète"."""
    return "".join(
        char for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


# The provider tells us how long to wait: "Please retry in 15.56543398s".
RETRY_DELAY_PATTERN = re.compile(r"retry in\s+([\d.]+)\s*s", re.IGNORECASE)


def _suggested_retry_delay(error: Exception) -> Optional[float]:
    """Extract the retry delay announced by the provider, if any."""
    match = RETRY_DELAY_PATTERN.search(str(error))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


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
        # Locked on the first turn: the AI mirrors the language of the user's
        # initial message for the whole conversation (PRD 3.1).
        self.initial_language: Optional[str] = None
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
        # Primary model first, then the configured fallbacks (deduplicated).
        candidates = [model] + list(GEMINI_MODEL_FALLBACKS or [])
        self.models = list(dict.fromkeys(m for m in candidates if m))
        self.system_prompt = SYSTEM_PROMPT_V1

    @staticmethod
    def _is_transient(error: Exception) -> bool:
        """Return True for rate limits and temporary upstream failures."""
        code = getattr(error, "code", None)
        if not isinstance(code, int):
            return False
        return code in TRANSIENT_STATUS_CODES or 500 <= code < 600

    def _generate_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            temperature=0.3,  # Lower temp for more consistent extraction
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
            response_mime_type="application/json",
            response_schema=OrderExtractionResponse,
        )

    def _generate_content(self, prompt: str) -> Any:
        """
        Call Gemini, retrying transient failures and falling back to other models.

        Retries only happen for rate limits and 5xx errors. Configuration and
        authentication failures (400/401/403/404) are never retried, because
        retrying them just delays the error the operator needs to see.
        """
        last_error: Optional[Exception] = None

        for model in self.models:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=self._generate_config(),
                    )
                    if not response.text:
                        raise ValueError(f"Gemini ({model}) returned an empty response")
                    return response
                except genai_errors.APIError as error:
                    last_error = error
                    if not self._is_transient(error):
                        logger.error(
                            "Gemini call failed permanently (model=%s, code=%s): %s",
                            model,
                            getattr(error, "code", None),
                            error,
                        )
                        break
                    if attempt >= MAX_RETRIES:
                        logger.error(
                            "Gemini call exhausted retries (model=%s, code=%s): %s",
                            model,
                            getattr(error, "code", None),
                            error,
                        )
                        break
                    delay = self._retry_delay(error, attempt)
                    logger.warning(
                        "Gemini call failed (model=%s, attempt=%d/%d, code=%s): %s. "
                        "Retrying in %.1fs",
                        model,
                        attempt,
                        MAX_RETRIES,
                        getattr(error, "code", None),
                        error,
                        delay,
                    )
                    time.sleep(delay)
                except ValueError:
                    raise
                except Exception as error:  # noqa: BLE001 - surfaced to the caller
                    last_error = error
                    logger.error("Unexpected error while calling Gemini (%s): %s", model, error)
                    break

        if last_error is None:
            raise RuntimeError("No Gemini model configured")
        raise last_error

    
    def _detect_language(self, message: str) -> str:
        """
        Detect the language/dialect of a message.

        Order matters: Arabic script wins first, then Franco-Arabic (which
        contains many French loanwords), then French, then English. Digits
        alone are never a signal: "Bonjour, prix 2500 DA" is French.
        """
        text = (message or "").strip()
        if not text:
            return "franco_arabic"

        # 1. Darija written in Arabic script.
        arabic_chars = sum(
            1 for c in text if "\u0600" <= c <= "\u06FF" or "\u0750" <= c <= "\u077F"
        )
        if arabic_chars / len(text) > 0.3:
            return "darija"

        lowered = text.casefold()

        # 2. Franco-Arabic (Darija in Latin script).
        if any(phrase in lowered for phrase in FRANCO_ARABIC_PHRASES):
            return "franco_arabic"
        if FRANCO_ARABIC_DIGIT_PATTERN.search(lowered):
            return "franco_arabic"
        tokens = set(re.findall(r"[a-z0-9']+", lowered))
        if tokens & set(FRANCO_ARABIC_MARKERS):
            return "franco_arabic"

        # 3. French, then English.
        if tokens & set(FRENCH_MARKERS):
            return "french"
        if tokens & set(ENGLISH_MARKERS):
            return "english"
        if any(marker in lowered for marker in ENGLISH_MARKERS):
            return "english"

        # French is the most common written language of the target market.
        return "french"
    
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
            elif field == "phone_number":
                # Re-validate on every turn: a stored value must stay a valid
                # Algerian number, not merely a non-empty string.
                if normalize_algerian_phone(value) is None:
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
        
        # Detect language. The PRD mirror rule locks the language of the very
        # first message for the rest of the conversation.
        detected_lang = self._detect_language(user_message)
        if conversation_state.initial_language is None:
            conversation_state.initial_language = detected_lang
        conversation_state.language = conversation_state.initial_language
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
Respond with a helpful message in the user's language ({conversation_state.language}), AND extract any order information into valid JSON matching the exact schema.
If escalation is needed (frustrated, bulk pricing request, or 3 failed data-collection attempts), set order_status to "REQUIRES_HUMAN".
Only set order_status to "CONFIRMED" if ALL 5 Sacred Fields are valid AND user explicitly confirms.

Return only the JSON object matching this exact shape:
{{"reply_to_customer": "message", "conversation_state": "INQUIRY|ORDER_INTENT|DATA_COLLECTION|CONFIRMATION", "extracted_data": {{"customer_name": null, "phone_number": null, "wilaya_code": null, "delivery_type": null, "address": null, "order_items": [], "subtotal_da": null, "shipping_fee_da": null, "total_price_da": null, "order_status": "PENDING_CONFIRMATION"}}}}

Be precise and follow all guardrails.
"""
        
        try:
            # Call Gemini API (retries + model fallbacks handled internally)
            response = self._generate_content(full_prompt)
            
            response_text_raw = response.text if response.text else ""
            
            # Parse JSON response
            parsed = self._parse_ai_response(response_text_raw)
            parsed = self._sanitize_extraction(parsed)
            extraction = OrderExtractionResponse.model_validate(parsed)
            response_text = extraction.reply_to_customer
            order_data = extraction.extracted_data.model_dump(mode="json")
            
            # Validate and update conversation state
            self._update_conversation_state(
                conversation_state,
                order_data,
                user_message,
                response_text,
                model_state=parsed.get("conversation_state"),
            )
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
            
        except genai_errors.APIError as error:
            # Configuration / auth / model errors must not look like a user error.
            code = getattr(error, "code", None)
            if self._is_transient(error):
                logger.warning("Gemini unavailable (transient, code=%s): %s", code, error)
                error_detail = f"AI provider temporarily unavailable (code {code})"
            else:
                logger.error("Gemini configuration error (code=%s): %s", code, error)
                error_detail = f"AI provider configuration error (code {code}): {error}"
            return self._build_fallback_result(conversation_state, error_detail)

        except Exception as error:  # noqa: BLE001 - never crash the webhook
            logger.exception("Unexpected failure while processing the message")
            return self._build_fallback_result(
                conversation_state,
                f"AI response could not be generated or validated: {error}",
            )

    def _build_fallback_result(
        self,
        conversation_state: ConversationState,
        error_detail: str,
    ) -> Dict[str, Any]:
        """Build the degraded response used when the AI pipeline fails."""
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
            "language": conversation_state.language,
            "error": error_detail,
        }
    
    def _sanitize_extraction(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize the raw model output before strict validation.

        The model occasionally returns a slightly malformed field (a phone
        number with a typo, a wilaya code out of range, a delivery type in
        the wrong case). Validating strictly would raise and throw away every
        other field the model did extract, losing the whole order. Invalid
        values are therefore dropped to None here, and the strict Pydantic
        contract still runs afterwards.
        """
        if not isinstance(parsed, dict):
            return parsed

        data = parsed.get("extracted_data")
        if not isinstance(data, dict):
            data = {}
        data = dict(data)

        # Phone number: keep it only when it is a valid Algerian mobile.
        data["phone_number"] = normalize_algerian_phone(data.get("phone_number"))

        # Wilaya code: keep it only when it maps to a known wilaya.
        wilaya_code = data.get("wilaya_code")
        if wilaya_code is not None:
            try:
                wilaya_code = int(wilaya_code)
            except (TypeError, ValueError):
                wilaya_code = None
            if wilaya_code is None or get_wilaya_name(wilaya_code) is None:
                wilaya_code = None
        data["wilaya_code"] = wilaya_code

        # Delivery type: case-insensitive, restricted to the enum values.
        delivery_type = data.get("delivery_type")
        if delivery_type is not None:
            delivery_type = str(delivery_type).strip().upper()
            if delivery_type not in {item.value for item in DeliveryType}:
                delivery_type = None
        data["delivery_type"] = delivery_type

        # Order status: fall back to the safe default when unknown.
        order_status = data.get("order_status")
        if order_status is not None:
            order_status = str(order_status).strip().upper()
            if order_status not in {item.value for item in OrderStatus}:
                order_status = OrderStatus.PENDING_CONFIRMATION.value
        else:
            order_status = OrderStatus.PENDING_CONFIRMATION.value
        data["order_status"] = order_status

        # Order items: drop malformed entries instead of failing the turn.
        items = data.get("order_items")
        cleaned_items: List[Dict[str, Any]] = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                product_name = item.get("product_name")
                if not isinstance(product_name, str) or not product_name.strip():
                    continue
                try:
                    quantity = int(item.get("quantity") or 1)
                except (TypeError, ValueError):
                    quantity = 1
                quantity = max(1, quantity)
                unit_price = item.get("unit_price_da")
                if unit_price is not None:
                    try:
                        unit_price = float(unit_price)
                    except (TypeError, ValueError):
                        unit_price = None
                    if unit_price is not None and unit_price < 0:
                        unit_price = None
                size_color = item.get("size_color")
                if size_color is not None and not isinstance(size_color, str):
                    size_color = str(size_color)
                cleaned_items.append({
                    "product_name": product_name.strip(),
                    "quantity": quantity,
                    "size_color": size_color,
                    "unit_price_da": unit_price,
                })
        data["order_items"] = cleaned_items

        # Monetary totals: negatives are meaningless, drop them.
        for price_field in ("subtotal_da", "shipping_fee_da", "total_price_da"):
            value = data.get(price_field)
            if value is None:
                continue
            try:
                value = float(value)
            except (TypeError, ValueError):
                data[price_field] = None
                continue
            data[price_field] = value if value >= 0 else None

        sanitized = dict(parsed)
        sanitized["extracted_data"] = data

        reply = sanitized.get("reply_to_customer")
        if not isinstance(reply, str):
            sanitized["reply_to_customer"] = "" if reply is None else str(reply)

        return sanitized

    def _retry_delay(self, error: Exception, attempt: int) -> float:
        """
        How long to wait before the next attempt.

        The exponential backoff is the baseline, but the provider knows better
        than we do: the Gemini free tier answers 429 with the delay it
        expects ("Please retry in 15.5s"), and retrying earlier only burns
        the remaining attempts.
        """
        delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
        suggested = _suggested_retry_delay(error)
        if suggested is not None:
            delay = max(delay, suggested)
        return min(delay, RETRY_MAX_DELAY)

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
        model_state: Optional[str] = None,
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
                    if field == "phone_number":
                        # Never store an invalid phone number: it would make
                        # the field look collected while failing validation.
                        val = normalize_algerian_phone(val)
                        if val is None:
                            continue
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
        # Resolution order: hard guardrails first, then a monotonic rule that
        # never lets the flow regress once an order has started, then the
        # intent heuristics, then the state reported by the model.
        intent = self._signals_order_intent(user_msg)
        has_items = bool(state.product_context.get("order_items"))
        if state.escalated:
            state.state = "ESCALATION"
        elif not state.missing_fields:
            # All fields collected
            state.state = "CONFIRMATION"
        elif state.collected_fields:
            # Once a field is collected we are in data collection, whatever
            # the model reports: a mid-order question is still an open order.
            state.state = "DATA_COLLECTION"
        elif previous_state in {"ORDER_INTENT", "DATA_COLLECTION"}:
            # The order already started: stay in it, a garbled turn must not
            # send the customer back to the inquiry state.
            state.state = previous_state
        elif previous_state == "CONFIRMATION":
            state.state = "DATA_COLLECTION"
        elif intent:
            state.state = "ORDER_INTENT"
        elif model_state == "ORDER_INTENT":
            state.state = "ORDER_INTENT"
        elif model_state == "DATA_COLLECTION" and has_items:
            state.state = "DATA_COLLECTION"
        else:
            # Nothing collected, no purchase intent: a product question.
            state.state = "INQUIRY"

    def _signals_order_intent(self, message: str) -> bool:
        """
        Detect an unambiguous purchase intent.

        Only high confidence expressions are listed here: this is the
        fallback used when the model does not report a state, so a false
        positive would push a price question into the ordering flow.
        """
        text = _strip_accents((message or "").casefold())
        return any(marker in text for marker in ORDER_INTENT_MARKERS)
    
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
