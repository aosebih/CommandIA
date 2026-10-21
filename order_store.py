"""
Supabase persistence for extracted orders.

The payload written to the database is the canonical contract from
roadmap.txt (lines 160-174), the same shape the AI module already produces
in ``order_data``. Writes go through the Supabase REST API so the service
keeps a single HTTP dependency (httpx) and no database driver.

The feature is disabled as long as SUPABASE_URL / SUPABASE_KEY still hold the
placeholder values from the .env template.
"""
import logging
from typing import Any, Dict, Optional

import httpx

from config import (
    SUPABASE_ENABLED,
    SUPABASE_KEY,
    SUPABASE_ORDERS_TABLE,
    SUPABASE_URL,
)

logger = logging.getLogger("commandia.order_store")

# The canonical order contract, in the order used by the database.
ORDER_COLUMNS = (
    "order_id",
    "customer_name",
    "phone_number",
    "wilaya",
    "delivery_type",
    "address",
    "product_details",
    "total_price_da",
    "order_status",
)


class OrderStore:
    """Write orders to Supabase. Silently disabled when not configured."""

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        table: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.url = (url if url is not None else SUPABASE_URL or "").rstrip("/")
        self.key = key if key is not None else SUPABASE_KEY
        self.table = table or SUPABASE_ORDERS_TABLE
        self.timeout = timeout
        self.enabled = bool(
            self.url
            and self.key
            and not (self.url.startswith("your_") and self.url.endswith("_here"))
            and not (self.key.startswith("your_") and self.key.endswith("_here"))
        )

    @property
    def endpoint(self) -> str:
        return f"{self.url}/rest/v1/{self.table}"

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.key or "",
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    def save_order(self, order: Dict[str, Any]) -> bool:
        """
        Persist a single order.

        Returns True when the row was accepted. A failure never breaks the
        conversation: the error is logged and the customer still gets an
        answer.
        """
        if not self.enabled:
            logger.info("Supabase is not configured, order %s not persisted",
                        order.get("order_id"))
            return False

        row = {column: order.get(column) for column in ORDER_COLUMNS}
        row["order_id"] = row["order_id"] or None

        try:
            response = httpx.post(
                self.endpoint,
                json=row,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except httpx.HTTPError as error:
            logger.error("Supabase write failed for order %s: %s",
                         order.get("order_id"), error)
            return False

        if response.status_code >= 300:
            logger.error(
                "Supabase returned %s for order %s: %s",
                response.status_code,
                order.get("order_id"),
                response.text[:500],
            )
            return False

        logger.info("Order %s persisted to Supabase", order.get("order_id"))
        return True


def save_order(order: Dict[str, Any]) -> bool:
    """Module level helper using the configured store."""
    return OrderStore().save_order(order)
