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
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api_routes import router as api_router
from config import (
    COMMANDIA_API_KEY,
    CORS_ORIGINS,
    HOST,
    META_ACCESS_TOKEN,
    META_APP_SECRET,
    META_GRAPH_API_VERSION,
    META_PAGE_ID,
    META_VERIFY_TOKEN,
    PORT,
    is_configured,
)
from order_store import OrderStore

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)

order_store = OrderStore()

# The AI service is created lazily so the container still starts (and
# /healthz still answers) when the API key is missing.
_ai_service = None
_ai_service_error: Optional[str] = None


def get_ai_service():
    """Return the shared AIService, creating it on first use."""
    global _ai_service, _ai_service_error
    if _ai_service is None:
        from ai_service import AIService

        try:
            _ai_service = AIService()
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

    url = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}/me/messages"
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
    """Flatten the Meta webhook payload into a list of incoming messages."""
    messages: List[Dict[str, Any]] = []
    for entry in payload.get("entry", []) or []:
        for messaging in entry.get("messaging", []) or []:
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
                "timestamp": messaging.get("timestamp"),
            })
    return messages


def _handle_incoming_message(message: Dict[str, Any]) -> None:
    """Process one incoming message and answer the customer."""
    sender_id = message["sender_id"]
    text = message["text"]

    logger.info("Incoming message from %s: %s", sender_id, text[:120])

    try:
        service = get_ai_service()
    except Exception as error:  # noqa: BLE001 - never crash the webhook
        logger.error("AI service unavailable: %s", error)
        return

    try:
        result = service.process_message(user_message=text)
    except Exception as error:  # noqa: BLE001 - never crash the webhook
        logger.exception("Failed to process the message")
        return

    order_status = (result.get("extracted_data") or {}).get("order_status")
    if order_status in {"CONFIRMED", "PENDING_CONFIRMATION"}:
        order = result.get("order_data") or {}
        if order.get("customer_name") and order.get("phone_number"):
            order_store.save_order(order)

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
def root():
    index = _frontend_dist / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {
        "service": "CommandIA AI Service",
        "docs": "/docs",
        "health": "/healthz",
        "api": "/api",
        "frontend": "http://localhost:5173 in development",
    }


# Serve the built React app when it exists. The catch-all is registered last so
# every API, webhook and documentation route keeps priority.
_frontend_dist = Path(
    os.getenv("COMMANDIA_FRONTEND_DIST", Path(__file__).resolve().parent / "frontend" / "dist")
)
if _frontend_dist.is_dir():
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str):
        reserved = ("api", "webhook", "healthz", "chat", "docs", "redoc", "openapi.json")
        if full_path == "api" or full_path.startswith("api/") or full_path.split("/", 1)[0] in reserved:
            raise HTTPException(status_code=404, detail="Not found")
        root_dir = _frontend_dist.resolve()
        candidate = (root_dir / full_path).resolve()
        if candidate != root_dir and root_dir not in candidate.parents:
            raise HTTPException(status_code=404, detail="Not found")
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(root_dir / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=HOST, port=PORT)
