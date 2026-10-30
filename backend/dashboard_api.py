"""Merchant dashboard REST API. Protected by COMMANDIA_API_KEY."""
from typing import Any, Dict, Optional

import hmac

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.config import COMMANDIA_API_KEY, DEFAULT_MERCHANT_ID, is_configured
from backend.conversation_store import ConversationStore
from backend.merchant_store import MerchantStore
from backend.order_store import OrderStore

router = APIRouter(prefix="/api", tags=["dashboard"])


def _require_key(x_api_key: Optional[str]) -> None:
    if not is_configured(COMMANDIA_API_KEY):
        raise HTTPException(status_code=503, detail="COMMANDIA_API_KEY is not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key, COMMANDIA_API_KEY):
        raise HTTPException(status_code=401, detail="invalid API key")


class StatusUpdate(BaseModel):
    order_status: str = Field(..., pattern="^(PENDING_CONFIRMATION|CONFIRMED|REQUIRES_HUMAN|CANCELLED)$")


class ProductPayload(BaseModel):
    id: Optional[str] = None
    merchant_id: Optional[str] = None
    name: str
    price_da: float
    stock_quantity: int = 0


class ShippingPayload(BaseModel):
    merchant_id: Optional[str] = None
    wilaya_code: int = Field(..., ge=1, le=69)
    home_fee_da: float
    desk_fee_da: float


class SettingsPayload(BaseModel):
    merchant_id: Optional[str] = None
    allows_desk_delivery: Optional[bool] = None
    bot_enabled: Optional[bool] = None
    store_name: Optional[str] = None


def register_dashboard(
    order_store: OrderStore,
    merchant_store: MerchantStore,
    conversation_store: ConversationStore,
) -> APIRouter:

    @router.get("/orders")
    def list_orders(
        merchant_id: Optional[str] = None,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Dict[str, Any]:
        _require_key(x_api_key)
        mid = merchant_id or DEFAULT_MERCHANT_ID
        return {"orders": order_store.list_orders(mid if mid and is_configured(mid) else None)}

    @router.get("/orders/{order_id}")
    def get_order(
        order_id: str,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Dict[str, Any]:
        _require_key(x_api_key)
        order = order_store.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="order not found")
        messages = []
        if order.get("conversation_id"):
            messages = conversation_store.list_messages(order["conversation_id"])
        return {"order": order, "messages": messages}

    @router.patch("/orders/{order_id}")
    def patch_order(
        order_id: str,
        payload: StatusUpdate,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Dict[str, Any]:
        _require_key(x_api_key)
        if not order_store.update_status(order_id, payload.order_status):
            raise HTTPException(status_code=502, detail="could not update order")
        return {"ok": True, "order_id": order_id, "order_status": payload.order_status}

    @router.get("/products")
    def list_products(
        merchant_id: Optional[str] = None,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Dict[str, Any]:
        _require_key(x_api_key)
        mid = merchant_id or DEFAULT_MERCHANT_ID
        return {"products": merchant_store.list_products(mid if mid and is_configured(mid) else None)}

    @router.post("/products")
    def upsert_product(
        payload: ProductPayload,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Dict[str, Any]:
        _require_key(x_api_key)
        data = payload.model_dump()
        data["merchant_id"] = data.get("merchant_id") or DEFAULT_MERCHANT_ID
        if not data.get("id"):
            data.pop("id", None)
        saved = merchant_store.upsert_product(data)
        if not saved:
            raise HTTPException(status_code=502, detail="could not save product")
        return {"product": saved}

    @router.get("/shipping")
    def list_shipping(
        merchant_id: Optional[str] = None,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Dict[str, Any]:
        _require_key(x_api_key)
        mid = merchant_id or DEFAULT_MERCHANT_ID
        return {"rates": merchant_store.list_shipping_rates(mid if mid and is_configured(mid) else None)}

    @router.post("/shipping")
    def upsert_shipping(
        payload: ShippingPayload,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Dict[str, Any]:
        _require_key(x_api_key)
        data = payload.model_dump()
        data["merchant_id"] = data.get("merchant_id") or DEFAULT_MERCHANT_ID
        saved = merchant_store.upsert_shipping_rate(data)
        if not saved:
            raise HTTPException(status_code=502, detail="could not save shipping rate")
        return {"rate": saved}

    @router.get("/settings")
    def get_settings(
        merchant_id: Optional[str] = None,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Dict[str, Any]:
        _require_key(x_api_key)
        merchant = merchant_store.get_merchant(merchant_id=merchant_id or DEFAULT_MERCHANT_ID)
        return {"merchant": merchant}

    @router.patch("/settings")
    def patch_settings(
        payload: SettingsPayload,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Dict[str, Any]:
        _require_key(x_api_key)
        merchant_id = payload.merchant_id or DEFAULT_MERCHANT_ID
        if not merchant_id or not is_configured(merchant_id):
            raise HTTPException(status_code=400, detail="DEFAULT_MERCHANT_ID is not configured")
        fields = payload.model_dump(exclude_none=True)
        fields.pop("merchant_id", None)
        if not merchant_store.update_merchant(merchant_id, fields):
            raise HTTPException(status_code=502, detail="could not update settings")
        return {"ok": True}

    return router
