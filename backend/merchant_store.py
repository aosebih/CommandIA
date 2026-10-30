"""Merchant catalog, shipping rates, and bot settings."""
import logging
from typing import Any, Dict, List, Optional

from backend.config import (
    DEFAULT_MERCHANT_ID,
    META_PAGE_ID,
    SUPABASE_KEY,
    SUPABASE_MERCHANTS_TABLE,
    SUPABASE_PRODUCTS_TABLE,
    SUPABASE_SHIPPING_TABLE,
    SUPABASE_URL,
    is_configured,
)
from backend.supabase_client import SupabaseRest

logger = logging.getLogger("commandia.merchant_store")


class MerchantStore:
    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        timeout: float = 10.0,
        client: Optional[SupabaseRest] = None,
    ):
        self.url = (url if url is not None else SUPABASE_URL or "").rstrip("/")
        self.key = key if key is not None else SUPABASE_KEY
        self.enabled = bool(self.url and is_configured(self.key) and is_configured(self.url))
        self.client = client or (
            SupabaseRest(self.url, self.key or "", timeout=timeout) if self.enabled else None
        )

    def get_merchant(
        self,
        page_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled or self.client is None:
            return None
        params: Dict[str, Any] = {"select": "*"}
        if merchant_id and is_configured(merchant_id):
            params["id"] = f"eq.{merchant_id}"
        elif page_id and is_configured(page_id):
            params["meta_page_id"] = f"eq.{page_id}"
        elif DEFAULT_MERCHANT_ID and is_configured(DEFAULT_MERCHANT_ID):
            params["id"] = f"eq.{DEFAULT_MERCHANT_ID}"
        else:
            params["limit"] = "1"
        rows = self.client.get(SUPABASE_MERCHANTS_TABLE, params)
        return rows[0] if rows else None

    def list_products(self, merchant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.enabled or self.client is None:
            return []
        params: Dict[str, Any] = {"select": "*", "order": "created_at.desc"}
        if merchant_id:
            params["merchant_id"] = f"eq.{merchant_id}"
        return self.client.get(SUPABASE_PRODUCTS_TABLE, params)

    def upsert_product(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.enabled or self.client is None:
            return None
        method = "PATCH" if product.get("id") else "POST"
        params = {"id": f"eq.{product['id']}"} if product.get("id") else None
        prefer = "return=representation"
        response = self.client.request(
            method,
            SUPABASE_PRODUCTS_TABLE,
            json=product,
            params=params,
            prefer=prefer,
        )
        if response.status_code >= 300:
            logger.error("Product write failed: %s", response.text[:400])
            return None
        body = response.json()
        if isinstance(body, list):
            return body[0] if body else product
        return body

    def list_shipping_rates(self, merchant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.enabled or self.client is None:
            return []
        params: Dict[str, Any] = {"select": "*", "order": "wilaya_code.asc"}
        if merchant_id:
            params["merchant_id"] = f"eq.{merchant_id}"
        return self.client.get(SUPABASE_SHIPPING_TABLE, params)

    def upsert_shipping_rate(self, rate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.enabled or self.client is None:
            return None
        response = self.client.request(
            "POST",
            SUPABASE_SHIPPING_TABLE,
            json=rate,
            prefer="resolution=merge-duplicates,return=representation",
        )
        if response.status_code >= 300:
            logger.error("Shipping write failed: %s", response.text[:400])
            return None
        body = response.json()
        return body[0] if isinstance(body, list) and body else body

    def update_merchant(self, merchant_id: str, fields: Dict[str, Any]) -> bool:
        if not self.enabled or self.client is None:
            return False
        response = self.client.request(
            "PATCH",
            SUPABASE_MERCHANTS_TABLE,
            json=fields,
            params={"id": f"eq.{merchant_id}"},
        )
        return response.status_code < 300

    def product_context_for(self, page_id: Optional[str] = None) -> Dict[str, Any]:
        """Catalog snapshot injected into the AI brain for a webhook turn."""
        merchant = self.get_merchant(page_id=page_id or META_PAGE_ID)
        if not merchant:
            return {}
        products = self.list_products(merchant["id"])
        rates = self.list_shipping_rates(merchant["id"])
        shipping_rates: Dict[str, Dict[str, float]] = {}
        for rate in rates:
            shipping_rates[str(rate["wilaya_code"])] = {
                "HOME": float(rate.get("home_fee_da") or 0),
                "DESK": float(rate.get("desk_fee_da") or 0),
            }
        primary = products[0] if products else {}
        return {
            "merchant_id": merchant["id"],
            "store_name": merchant.get("store_name"),
            "allows_desk_delivery": bool(merchant.get("allows_desk_delivery", True)),
            "bot_enabled": bool(merchant.get("bot_enabled", True)),
            "catalog": [
                {
                    "item_id": product["id"],
                    "name": product["name"],
                    "price": float(product["price_da"]),
                    "stock_quantity": product.get("stock_quantity"),
                }
                for product in products
            ],
            "shipping_rates": shipping_rates,
            "item_id": primary.get("id"),
            "name": primary.get("name"),
            "price": float(primary["price_da"]) if primary.get("price_da") is not None else None,
            "quantity": 1,
        }
