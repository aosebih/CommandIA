"""Application API consumed by the React frontend.

All routes live under ``/api`` and use the same compact field names as the
frontend domain types. Data is persisted locally by :mod:`local_store`.
"""
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

import config  # noqa: F401 - loads .env before auth reads its secrets

from auth import (
    COOKIE_NAME,
    SESSION_TTL_SECONDS,
    create_session_token,
    verify_password,
    verify_session_token,
)
from local_ai import fallback_result
from local_store import LocalStore
from wilayas import get_wilaya_name

logger = logging.getLogger("commandia.api")

router = APIRouter(prefix="/api")
store = LocalStore()

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COOKIE_SECURE = config.COOKIE_SECURE
COOKIE_SAMESITE = config.COOKIE_SAMESITE

INTENT_BY_STATE = {
    "INQUIRY": "Product inquiry",
    "ORDER_INTENT": "Ready to order",
    "DATA_COLLECTION": "Collecting order details",
    "CONFIRMATION": "Order ready for confirmation",
    "ESCALATION": "Needs human review",
}


class SignUpPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=6, max_length=256)


class SignInPayload(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=256)


class ModePayload(BaseModel):
    mode: Literal["ai", "attn", "manual"]


class MessagePayload(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class OrderStatusPayload(BaseModel):
    status: Literal["await", "confirmed", "shipped", "delivered", "cancelled"]


class ProductPayload(BaseModel):
    n: str = Field(..., min_length=1, max_length=200)
    p: float = Field(..., ge=0)
    s: int = Field(..., ge=0)


class AIStatusPayload(BaseModel):
    enabled: bool


class RulesPayload(BaseModel):
    zones: Dict[str, float] = Field(default_factory=dict)
    opens: str = "09:00"
    closes: str = "18:00"
    behavior: str = "Flag for human intervention"
    instructions: str = ""
    tone: str = "Warm and concise"
    languages: str = "French / Algerian Arabic"
    maxDiscount: float = Field(default=0, ge=0)
    freeAbove: float = Field(default=0, ge=0)


def _set_session(response: Response, email: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_session_token(email),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path="/",
    )


def current_user(request: Request) -> Dict[str, str]:
    email = verify_session_token(request.cookies.get(COOKIE_NAME))
    user = store.find_user(email) if email else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return store.public_user(user)


def _now_label() -> str:
    return datetime.now().strftime("%H:%M")


def _normalize_email(email: str) -> str:
    clean = email.strip().lower()
    if not EMAIL_PATTERN.match(clean):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    return clean


# --- Authentication -------------------------------------------------------------


@router.post("/auth/sign-up")
def sign_up(payload: SignUpPayload, response: Response) -> Dict[str, str]:
    email = _normalize_email(payload.email)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    try:
        user = store.create_user(name, email, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    _set_session(response, email)
    return user


@router.post("/auth/sign-in")
def sign_in(payload: SignInPayload, response: Response) -> Dict[str, str]:
    email = _normalize_email(payload.email)
    user = store.find_user(email)
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    _set_session(response, email)
    return store.public_user(user)


@router.post("/auth/sign-out")
def sign_out(response: Response) -> Dict[str, bool]:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(user: Dict[str, str] = Depends(current_user)) -> Dict[str, str]:
    return user


# --- Conversations --------------------------------------------------------------


@router.get("/conversations")
def conversations(user: Dict[str, str] = Depends(current_user)) -> List[Dict[str, Any]]:
    return store.conversations()


@router.patch("/conversations/{conversation_id}/mode")
def set_conversation_mode(
    conversation_id: int,
    payload: ModePayload,
    user: Dict[str, str] = Depends(current_user),
) -> str:
    if store.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return store.update_mode(conversation_id, payload.mode)


def _ai_result(conversation: Dict[str, Any], text: str) -> Dict[str, Any]:
    try:
        from app import get_ai_service

        service = get_ai_service()
        return service.process_message(
            user_message=text,
            conversation_id=f"web-{conversation['id']}",
            product_context={
                "products": store.products(),
                "business_rules": store.rules(),
            },
        )
    except Exception as error:  # noqa: BLE001 - offline fallback is intentional
        logger.info("Gemini unavailable, using local reply: %s", error)
        return fallback_result(text, conversation, store.products(), store.rules())


def _intent_for(result: Dict[str, Any]) -> str:
    intent = result.get("intent")
    if isinstance(intent, str) and intent:
        return intent
    return INTENT_BY_STATE.get(str(result.get("state", "")), "Customer conversation")


def _order_from_result(conversation: Dict[str, Any], result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    extracted = result.get("extracted_data") or {}
    legacy = result.get("order_data") or {}
    required = ("customer_name", "phone_number", "wilaya_code", "delivery_type", "address")
    if any(not extracted.get(field) for field in required):
        return None
    if extracted.get("order_status") == "REQUIRES_HUMAN":
        return None
    if store.find_order_for_conversation(conversation["id"]):
        return None

    items = extracted.get("order_items") or []
    total = extracted.get("total_price_da") or legacy.get("total_price_da")
    if total is None:
        subtotal = sum(
            float(item.get("unit_price_da") or 0) * int(item.get("quantity") or 1)
            for item in items
        )
        total = subtotal + float(extracted.get("shipping_fee_da") or 0)

    delivery = str(extracted.get("delivery_type") or "HOME").upper()
    order = {
        "name": str(extracted["customer_name"]),
        "ph": str(extracted["phone_number"]),
        "wil": legacy.get("wilaya") or get_wilaya_name(int(extracted["wilaya_code"])) or "Unknown",
        "del": "Stop-desk" if delivery == "DESK" else "Home delivery",
        "addr": str(extracted["address"]),
        "tot": round(float(total or 0)),
        "st": "await",
        "d": datetime.now().strftime("%d %b %Y"),
        "conversationId": conversation["id"],
    }
    created = store.create_order(order)
    store.update_conversation(conversation["id"], oid=created["id"], intent="Order collected")
    return created


@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: int,
    payload: MessagePayload,
    user: Dict[str, str] = Depends(current_user),
) -> Dict[str, Any]:
    conversation = store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message text is required")

    human_message = {"w": "h", "t": text, "time": _now_label()}
    store.append_message(conversation_id, human_message)

    reply_message: Optional[Dict[str, str]] = None
    current = store.get_conversation(conversation_id) or conversation
    if current.get("m") == "ai" and store.settings().get("ai"):
        result = _ai_result(current, text)
        reply_text = str(result.get("reply_to_customer") or result.get("response_text") or "").strip()
        if reply_text:
            reply_message = {"w": "a", "t": reply_text, "time": _now_label()}
            store.append_message(conversation_id, reply_message)

        intent = _intent_for(result)
        updates: Dict[str, Any] = {"intent": intent}
        extracted = result.get("extracted_data") or {}
        if extracted.get("order_status") == "REQUIRES_HUMAN":
            updates["m"] = "attn"
            updates["why"] = "The AI flagged this conversation for human review."
        store.update_conversation(conversation_id, **updates)
        _order_from_result(current, result)

    updated = store.get_conversation(conversation_id) or conversation
    return {
        "message": human_message,
        "reply": reply_message,
        "mode": updated.get("m", "ai"),
        "intent": updated.get("intent"),
    }


# --- Orders ---------------------------------------------------------------------


@router.get("/orders")
def orders(user: Dict[str, str] = Depends(current_user)) -> List[Dict[str, Any]]:
    return store.orders()


@router.patch("/orders/{order_id}/status")
def set_order_status(
    order_id: int,
    payload: OrderStatusPayload,
    user: Dict[str, str] = Depends(current_user),
) -> str:
    try:
        return store.set_order_status(order_id, payload.status)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Order not found") from error


# --- Products -------------------------------------------------------------------


@router.get("/products")
def products(user: Dict[str, str] = Depends(current_user)) -> List[Dict[str, Any]]:
    return store.products()


@router.post("/products")
def create_product(
    payload: ProductPayload,
    user: Dict[str, str] = Depends(current_user),
) -> Dict[str, Any]:
    return store.save_product(payload.model_dump())


@router.put("/products/{product_id}")
def update_product(
    product_id: int,
    payload: ProductPayload,
    user: Dict[str, str] = Depends(current_user),
) -> Dict[str, Any]:
    if not any(int(product["id"]) == product_id for product in store.products()):
        raise HTTPException(status_code=404, detail="Product not found")
    return store.save_product({**payload.model_dump(), "id": product_id})


# --- Settings, integrations and rules -------------------------------------------


@router.get("/settings")
def settings(user: Dict[str, str] = Depends(current_user)) -> Dict[str, bool]:
    return store.settings()


@router.patch("/settings/ai")
def set_ai(
    payload: AIStatusPayload,
    user: Dict[str, str] = Depends(current_user),
) -> Dict[str, bool]:
    return store.set_ai(payload.enabled)


@router.post("/integrations/instagram/connect")
def connect_instagram(user: Dict[str, str] = Depends(current_user)) -> Dict[str, bool]:
    return store.set_instagram(True)


@router.post("/integrations/instagram/disconnect")
def disconnect_instagram(user: Dict[str, str] = Depends(current_user)) -> Dict[str, bool]:
    return store.set_instagram(False)


@router.get("/rules")
def rules(user: Dict[str, str] = Depends(current_user)) -> Dict[str, Any]:
    return store.rules()


@router.put("/rules")
def save_rules(
    payload: RulesPayload,
    user: Dict[str, str] = Depends(current_user),
) -> Dict[str, Any]:
    return store.save_rules(payload.model_dump())
