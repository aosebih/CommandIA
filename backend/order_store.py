"""
Supabase persistence for extracted orders and line items.

Writes follow backend/schema.sql. A malformed or partial extraction never
breaks the customer reply: failures are logged and ignored.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional

import httpx

from backend.config import (
    SUPABASE_ENABLED,
    SUPABASE_KEY,
    SUPABASE_ORDER_ITEMS_TABLE,
    SUPABASE_ORDERS_TABLE,
    SUPABASE_URL,
    is_configured,
)
from backend.supabase_client import SupabaseRest
from ai.wilayas import get_wilaya_code, get_wilaya_name

logger = logging.getLogger("commandia.order_store")

ORDER_COLUMNS = (
    "order_id",
    "merchant_id",
    "conversation_id",
    "customer_name",
    "phone_number",
    "wilaya_code",
    "delivery_type",
    "address",
    "subtotal_da",
    "shipping_fee_da",
    "total_price_da",
    "order_status",
)
DERIVED_COLUMNS = ("wilaya_name",)

SACRED_FIELDS = (
    "customer_name",
    "phone_number",
    "wilaya_code",
    "delivery_type",
    "address",
)


def sacred_fields_complete(extracted: Dict[str, Any]) -> bool:
    for field in SACRED_FIELDS:
        value = extracted.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return False
    return True


class OrderStore:
    """Write orders to Supabase. Silently disabled when not configured."""

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        table: Optional[str] = None,
        items_table: Optional[str] = None,
        timeout: float = 10.0,
        client: Optional[SupabaseRest] = None,
    ):
        self.url = (url if url is not None else SUPABASE_URL or "").rstrip("/")
        self.key = key if key is not None else SUPABASE_KEY
        self.table = table or SUPABASE_ORDERS_TABLE
        self.items_table = items_table or SUPABASE_ORDER_ITEMS_TABLE
        self.timeout = timeout
        self.enabled = bool(self.url and is_configured(self.key) and is_configured(self.url))
        self.client = client or (
            SupabaseRest(self.url, self.key or "", timeout=timeout) if self.enabled else None
        )

    def _post(self, table: str, payload: Any, prefer: str = "return=representation"):
        assert self.client is not None
        return self.client.request("POST", table, json=payload, prefer=prefer)

    def _patch(self, table: str, params: Dict[str, str], payload: Dict[str, Any]):
        assert self.client is not None
        return self.client.request(
            "PATCH", table, json=payload, params=params, prefer="return=representation"
        )

    def _delete(self, table: str, params: Dict[str, str]) -> bool:
        assert self.client is not None
        response = self.client.request("DELETE", table, params=params)
        return response.status_code < 300

    def save_order(self, order: Dict[str, Any]) -> bool:
        """Persist a single order and its line items. Returns True on success."""
        if not self.enabled or self.client is None:
            logger.info("Supabase is not configured, order %s not persisted",
                        order.get("order_id"))
            return False

        row = self._order_row(order)
        items = self._item_rows(order, row["order_id"])

        try:
            if order.get("_existing"):
                response = self._patch(
                    self.table,
                    {"order_id": f"eq.{row['order_id']}"},
                    row,
                )
            else:
                response = self._post(self.table, row)
        except httpx.HTTPError as error:
            logger.error("Supabase write failed for order %s: %s",
                         row.get("order_id"), error)
            return False

        if response.status_code >= 300:
            logger.error(
                "Supabase returned %s for order %s: %s",
                response.status_code,
                row.get("order_id"),
                response.text[:500],
            )
            return False

        if items:
            try:
                self._delete(self.items_table, {"order_id": f"eq.{row['order_id']}"})
                item_response = self._post(self.items_table, items)
            except httpx.HTTPError as error:
                logger.error("Supabase item write failed for order %s: %s",
                             row.get("order_id"), error)
                return False
            if item_response.status_code >= 300:
                logger.error(
                    "Supabase returned %s for order items %s: %s",
                    item_response.status_code,
                    row.get("order_id"),
                    item_response.text[:500],
                )
                return False

        logger.info("Order %s persisted to Supabase", row.get("order_id"))
        return True

    def save_from_extraction(
        self,
        result: Dict[str, Any],
        *,
        merchant_id: Optional[str] = None,
        conversation_uuid: Optional[str] = None,
        existing_order_id: Optional[str] = None,
    ) -> Optional[str]:
        extracted = result.get("extracted_data") or {}
        collected = result.get("collected_fields") or {}
        merged = dict(extracted)
        for field in SACRED_FIELDS:
            if not merged.get(field) and collected.get(field):
                merged[field] = collected[field]
        if result.get("missing_fields"):
            return None
        if not sacred_fields_complete(merged):
            return None
        status = merged.get("order_status") or "PENDING_CONFIRMATION"
        if status not in {"PENDING_CONFIRMATION", "CONFIRMED", "REQUIRES_HUMAN"}:
            return None

        order_id = existing_order_id or str(uuid.uuid4())
        payload = {
            "order_id": order_id,
            "merchant_id": merchant_id,
            "conversation_id": conversation_uuid,
            "customer_name": merged.get("customer_name"),
            "phone_number": merged.get("phone_number"),
            "wilaya_code": merged.get("wilaya_code"),
            "delivery_type": merged.get("delivery_type"),
            "address": merged.get("address"),
            "subtotal_da": merged.get("subtotal_da"),
            "shipping_fee_da": merged.get("shipping_fee_da"),
            "total_price_da": merged.get("total_price_da"),
            "order_status": status,
            "order_items": merged.get("order_items") or [],
            "_existing": bool(existing_order_id),
        }
        if self.save_order(payload):
            return order_id
        return None

    def list_orders(self, merchant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.enabled or self.client is None:
            return []
        params: Dict[str, Any] = {"select": "*,order_items(*)", "order": "created_at.desc"}
        if merchant_id:
            params["merchant_id"] = f"eq.{merchant_id}"
        return self.client.get(self.table, params)

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        if not self.enabled or self.client is None:
            return None
        rows = self.client.get(
            self.table,
            {"select": "*,order_items(*)", "order_id": f"eq.{order_id}"},
        )
        return rows[0] if rows else None

    def update_status(self, order_id: str, order_status: str) -> bool:
        if not self.enabled or self.client is None:
            return False
        try:
            response = self._patch(
                self.table,
                {"order_id": f"eq.{order_id}"},
                {"order_status": order_status},
            )
        except httpx.HTTPError:
            return False
        return response.status_code < 300

    def _order_row(self, order: Dict[str, Any]) -> Dict[str, Any]:
        wilaya_code = order.get("wilaya_code")
        if wilaya_code is None and order.get("wilaya"):
            wilaya_code = get_wilaya_code(str(order["wilaya"]))
        try:
            wilaya_code = int(wilaya_code) if wilaya_code is not None else None
        except (TypeError, ValueError):
            wilaya_code = None

        row = {column: order.get(column) for column in ORDER_COLUMNS}
        row["order_id"] = row["order_id"] or str(uuid.uuid4())
        row["wilaya_code"] = wilaya_code
        row["wilaya_name"] = get_wilaya_name(wilaya_code) if wilaya_code else order.get("wilaya")
        row["order_status"] = order.get("order_status") or "PENDING_CONFIRMATION"
        return row

    def _item_rows(self, order: Dict[str, Any], order_id: str) -> List[Dict[str, Any]]:
        items = order.get("order_items")
        if not items:
            details = order.get("product_details") or {}
            if details:
                items = [{
                    "product_name": details.get("item_id") or details.get("product_name") or "Produit",
                    "quantity": details.get("quantity") or 1,
                    "size_color": details.get("size_color"),
                    "unit_price_da": details.get("unit_price_da"),
                }]
        rows = []
        for item in items or []:
            name = item.get("extracted_product_name") or item.get("product_name") or "Produit"
            rows.append({
                "order_id": order_id,
                "product_id": item.get("product_id"),
                "extracted_product_name": name,
                "quantity": int(item.get("quantity") or 1),
                "unit_price_da": item.get("unit_price_da"),
                "attributes": {"size_color": item.get("size_color")} if item.get("size_color") else None,
            })
        return rows


def save_order(order: Dict[str, Any]) -> bool:
    """Module level helper using the configured store."""
    return OrderStore().save_order(order)
