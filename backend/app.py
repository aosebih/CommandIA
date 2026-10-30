"""
CommandIA HTTP service.

Endpoints:
    GET  /healthz   liveness probe, public
    GET  /webhook   Meta verification challenge
    POST /webhook   Meta webhook (Instagram / Facebook DMs)
    POST /chat      development endpoint, protected by COMMANDIA_API_KEY

The Meta webhook answers 200 immediately and processes the message in the
background: Meta retries any request that is not answered within 20 seconds.
"""
import hashlib
import hmac
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from fastapi.middleware.cors import CORSMiddleware

from backend.config import (
    COMMANDIA_API_KEY,
    DASHBOARD_ORIGIN,
    HOST,
    META_ACCESS_TOKEN,
    META_APP_SECRET,
    META_GRAPH_API_VERSION,
    META_PAGE_ID,
    META_VERIFY_TOKEN,
    PORT,
    is_configured,
)
from backend.conversation_store import ConversationStore
from backend.dashboard_api import register_dashboard
from backend.merchant_store import MerchantStore
from backend.order_store import OrderStore, sacred_fields_complete

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("commandia.app")

app = FastAPI(
    title="CommandIA AI Service",
    version="1.0.0",
    description="CommandIA conversational AI for Algerian e-commerce.",
)

order_store = OrderStore()
conversation_store = ConversationStore()
merchant_store = MerchantStore()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[DASHBOARD_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(register_dashboard(order_store, merchant_store, conversation_store))

# The AI service is created lazily so the container still starts (and
# /healthz still answers) when the API key is missing.
_ai_service = None
_ai_service_error: Optional[str] = None


def get_ai_service():
    """Return the shared AIService, creating it on first use."""
    global _ai_service, _ai_service_error
    if _ai_service is None:
        from ai.ai_service import AIService

        try:
            _ai_service = AIService(conversation_store=conversation_store)
            _ai_service_error = None
        except Exception as error:  # noqa: BLE001 - reported through /healthz
            _ai_service_error = str(error)
            raise
    return _ai_service


def _ai_status() -> Dict[str, Any]:
    """Report whether the AI service can actually be built."""
    try:
        get_ai_service()
    except Exception:  # noqa: BLE001 - the error is kept in _ai_service_error
        pass
    return {"ai_ready": _ai_service is not None, "ai_error": _ai_service_error}


# --- Meta helpers ---------------------------------------------------------------

# Message ids already handled, so a Meta retry never answers twice.
_seen_message_ids: Set[str] = set()
_seen_message_ids_order: List[str] = []
MAX_SEEN_MESSAGE_IDS = 2000


def _remember_message(message_id: str) -> bool:
    """
    Register a message id. Returns False when it was already handled.
    """
    if not message_id:
        return True
    if message_id in _seen_message_ids:
        return False
    _seen_message_ids.add(message_id)
    _seen_message_ids_order.append(message_id)
    if len(_seen_message_ids_order) > MAX_SEEN_MESSAGE_IDS:
        oldest = _seen_message_ids_order.pop(0)
        _seen_message_ids.discard(oldest)
    return True


def _verify_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """Check the X-Hub-Signature-256 header against the app secret."""
    if not is_configured(META_APP_SECRET):
        logger.warning("META_APP_SECRET is not configured, cannot verify the signature")
        return False
    if not signature:
        return False
    expected = "sha256=" + hmac.new(
        META_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _send_meta_message(recipient_id: str, text: str) -> bool:
    """Send a reply through the Graph API."""
    if not is_configured(META_ACCESS_TOKEN):
        logger.warning("META_ACCESS_TOKEN is not configured, reply not sent")
        return False

    target = META_PAGE_ID if is_configured(META_PAGE_ID) else "me"
    url = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}/{target}/messages"
    payload: Dict[str, Any] = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    if META_PAGE_ID:
        payload["messaging_type"] = "RESPONSE"
        payload["recipient"] = {"id": recipient_id}

    try:
        response = httpx.post(
            url,
            json=payload,
            params={"access_token": META_ACCESS_TOKEN},
            timeout=10.0,
        )
    except httpx.HTTPError as error:
        logger.error("Graph API request failed: %s", error)
        return False

    if response.status_code >= 300:
        logger.error("Graph API returned %s: %s", response.status_code, response.text[:500])
        return False
    return True


def _extract_messages(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten Messenger and Instagram webhook payloads into incoming messages."""
    messages: List[Dict[str, Any]] = []
    for entry in payload.get("entry", []) or []:
        events = list(entry.get("messaging") or [])
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            events.extend(value.get("messaging") or [])
            for raw in value.get("messages") or []:
                events.append({
                    "sender": {"id": raw.get("from") or (value.get("sender") or {}).get("id")},
                    "recipient": {"id": value.get("recipient", {}).get("id") or entry.get("id")},
                    "timestamp": raw.get("timestamp") or value.get("timestamp"),
                    "message": raw,
                })
        for messaging in events:
            message = messaging.get("message") or {}
            text = (message.get("text") or "").strip()
            if not text:
                continue
            if message.get("is_echo"):
                continue
            messages.append({
                "mid": message.get("mid") or "",
                "text": text,
                "sender_id": (messaging.get("sender") or {}).get("id") or "",
                "recipient_id": (messaging.get("recipient") or {}).get("id") or entry.get("id") or "",
                "timestamp": messaging.get("timestamp"),
            })
    return messages


def _handle_incoming_message(message: Dict[str, Any]) -> None:
    """Process one incoming message and answer the customer."""
    sender_id = message["sender_id"]
    text = message["text"]
    page_id = message.get("recipient_id") or META_PAGE_ID

    logger.info("Incoming message from %s: %s", sender_id, text[:120])

    product_context = merchant_store.product_context_for(page_id)
    if product_context.get("bot_enabled") is False:
        logger.info("Bot disabled for merchant %s, skipping", product_context.get("merchant_id"))
        return

    try:
        service = get_ai_service()
    except Exception as error:  # noqa: BLE001 - never crash the webhook
        logger.error("AI service unavailable: %s", error)
        return

    try:
        result = service.process_message(
            user_message=text,
            conversation_id=sender_id,
            product_context=product_context,
            merchant_id=product_context.get("merchant_id"),
        )
    except Exception as error:  # noqa: BLE001 - never crash the webhook
        logger.exception("Failed to process the message")
        return

    extracted = result.get("extracted_data") or {}
    collected = result.get("collected_fields") or {}
    merged = dict(extracted)
    merged.update({k: v for k, v in collected.items() if v is not None})
    order_status = merged.get("order_status")
    if (
        order_status in {"CONFIRMED", "PENDING_CONFIRMATION", "REQUIRES_HUMAN"}
        and not result.get("missing_fields")
        and sacred_fields_complete(merged)
    ):
        service_state = None
        try:
            service_state = get_ai_service()._conversations.get(sender_id)
        except Exception:  # noqa: BLE001
            service_state = None
        existing_id = getattr(service_state, "open_order_id", None)
        saved_id = order_store.save_from_extraction(
            result,
            merchant_id=product_context.get("merchant_id") or getattr(service_state, "merchant_id", None),
            conversation_uuid=getattr(service_state, "db_conversation_id", None),
            existing_order_id=existing_id,
        )
        if saved_id and service_state is not None:
            service_state.open_order_id = saved_id
            conversation_store.save(
                service_state,
                customer_ig_id=sender_id,
                merchant_id=service_state.merchant_id,
            )

    reply = result.get("reply_to_customer")
    if not reply:
        return
    if not _send_meta_message(sender_id, reply):
        logger.warning("Reply not delivered to %s", sender_id)


# --- Endpoints ------------------------------------------------------------------


@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    """Liveness probe. Public on purpose: it exposes no secret."""
    status = _ai_status()
    return {
        "status": "ok" if status["ai_ready"] else "degraded",
        "ai_ready": status["ai_ready"],
        "ai_error": status["ai_error"],
        "supabase_enabled": order_store.enabled,
        "meta_configured": is_configured(META_ACCESS_TOKEN),
        "meta_verification_configured": is_configured(META_VERIFY_TOKEN),
        "chat_enabled": is_configured(COMMANDIA_API_KEY),
        "time": int(time.time()),
    }


@app.get("/webhook")
def webhook_verification(request: Request):
    """
    Meta verification challenge.

    The query parameters contain dots ("hub.mode"), which FastAPI cannot bind
    to a python identifier, so they are read from the raw query string.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    verify_token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode != "subscribe":
        return PlainTextResponse("unsupported mode", status_code=400)
    if not is_configured(META_VERIFY_TOKEN):
        logger.error("META_VERIFY_TOKEN is not configured")
        raise HTTPException(status_code=503, detail="META_VERIFY_TOKEN is not configured")
    if not verify_token or not hmac.compare_digest(verify_token, META_VERIFY_TOKEN):
        logger.warning("Webhook verification failed: bad verify token")
        raise HTTPException(status_code=403, detail="invalid verify token")
    if not challenge:
        raise HTTPException(status_code=400, detail="missing challenge")
    return PlainTextResponse(challenge)


@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(default=None, alias="X-Hub-Signature-256"),
):
    """Receive a Meta webhook, answer 200 and process the message in background."""
    raw_body = await request.body()

    if not is_configured(META_APP_SECRET):
        logger.error("META_APP_SECRET is not configured, rejecting the webhook")
        return JSONResponse({"status": "error", "detail": "META_APP_SECRET is not configured"},
                             status_code=503)
    if not _verify_signature(raw_body, x_hub_signature_256):
        logger.warning("Webhook signature verification failed")
        return JSONResponse({"status": "error", "detail": "invalid signature"},
                             status_code=403)

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 - malformed body
        logger.warning("Webhook body is not valid JSON")
        return JSONResponse({"status": "error", "detail": "invalid json"}, status_code=400)

    messages = _extract_messages(payload)
    fresh_messages = []
    for message in messages:
        if _remember_message(message["mid"]):
            fresh_messages.append(message)
        else:
            logger.info("Duplicate message %s ignored", message["mid"])

    for message in fresh_messages:
        background_tasks.add_task(_handle_incoming_message, message)

    return {"status": "ok", "received": len(fresh_messages)}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    product_context: Optional[Dict[str, Any]] = None


@app.post("/chat")
def chat(payload: ChatRequest, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """Development endpoint to exercise the AI brain over HTTP."""
    if not is_configured(COMMANDIA_API_KEY):
        raise HTTPException(status_code=503, detail="COMMANDIA_API_KEY is not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key, COMMANDIA_API_KEY):
        raise HTTPException(status_code=401, detail="invalid API key")

    try:
        service = get_ai_service()
    except Exception as error:  # noqa: BLE001
        logger.error("AI service unavailable: %s", error)
        raise HTTPException(status_code=503, detail=str(error))

    result = service.process_message(
        user_message=payload.message,
        conversation_id=payload.conversation_id,
        product_context=payload.product_context,
    )
    return {
        "reply_to_customer": result.get("reply_to_customer"),
        # Legacy alias, kept so an HTTP client sees the same keys as a
        # programmatic caller of AIService.process_message.
        "response_text": result.get("response_text"),
        "language": result.get("language"),
        "state": result.get("state"),
        "missing_fields": result.get("missing_fields"),
        "collected_fields": result.get("collected_fields"),
        "extracted_data": result.get("extracted_data"),
        "order_data": result.get("order_data"),
        "conversation_id": result.get("conversation_id"),
        "error": result.get("error"),
    }


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "service": "CommandIA AI Service",
        "docs": "/docs",
        "health": "/healthz",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host=HOST, port=PORT)
