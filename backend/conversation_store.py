"""Persist conversation state so a process restart does not reset a DM thread."""
import logging
from typing import Any, Dict, Optional

import httpx

from ai.ai_brain import ConversationState
from backend.config import (
    DEFAULT_MERCHANT_ID,
    SUPABASE_CONVERSATIONS_TABLE,
    SUPABASE_KEY,
    SUPABASE_MESSAGES_TABLE,
    SUPABASE_URL,
    is_configured,
)
from backend.supabase_client import SupabaseRest

logger = logging.getLogger("commandia.conversation_store")


class ConversationStore:
    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        timeout: float = 10.0,
        client: Optional[SupabaseRest] = None,
    ):
        self.url = (url if url is not None else SUPABASE_URL or "").rstrip("/")
        self.key = key if key is not None else SUPABASE_KEY
        self.conversations_table = SUPABASE_CONVERSATIONS_TABLE
        self.messages_table = SUPABASE_MESSAGES_TABLE
        self.enabled = bool(self.url and is_configured(self.key) and is_configured(self.url))
        self.client = client or (
            SupabaseRest(self.url, self.key or "", timeout=timeout) if self.enabled else None
        )

    def load(
        self,
        customer_ig_id: str,
        merchant_id: Optional[str] = None,
    ) -> Optional[ConversationState]:
        if not self.enabled or self.client is None or not customer_ig_id:
            return None
        merchant_id = merchant_id or DEFAULT_MERCHANT_ID
        params: Dict[str, Any] = {
            "select": "*",
            "customer_ig_id": f"eq.{customer_ig_id}",
        }
        if merchant_id and is_configured(merchant_id):
            params["merchant_id"] = f"eq.{merchant_id}"
        rows = self.client.get(self.conversations_table, params)
        if not rows:
            return None
        row = rows[0]
        state = ConversationState.from_dict({
            "conversation_id": customer_ig_id,
            "db_conversation_id": row.get("id"),
            "open_order_id": row.get("open_order_id"),
            "merchant_id": row.get("merchant_id"),
            "state": row.get("current_state") or "INQUIRY",
            "collected_fields": row.get("collected_fields") or {},
            "product_context": row.get("product_context") or {},
            "language": row.get("language") or "franco_arabic",
            "initial_language": row.get("language"),
            "attempts": row.get("attempts") or 0,
            "failed_data_attempts": row.get("failed_data_attempts") or 0,
            "escalated": bool(row.get("escalated")),
        })
        return state

    def save(
        self,
        state: ConversationState,
        *,
        customer_ig_id: str,
        merchant_id: Optional[str] = None,
        user_message: Optional[str] = None,
        bot_message: Optional[str] = None,
    ) -> Optional[str]:
        if not self.enabled or self.client is None:
            return None
        merchant_id = merchant_id or state.merchant_id or DEFAULT_MERCHANT_ID
        payload = {
            "merchant_id": merchant_id if merchant_id and is_configured(str(merchant_id)) else None,
            "customer_ig_id": customer_ig_id,
            "current_state": state.state if state.state != "ESCALATION" else "ESCALATION",
            "collected_fields": state.collected_fields,
            "product_context": state.product_context,
            "language": state.language,
            "attempts": state.attempts,
            "failed_data_attempts": state.failed_data_attempts,
            "escalated": state.escalated,
            "open_order_id": state.open_order_id,
            "last_message_at": "now()",
        }
        # PostgREST rejects the SQL now() string; omit and let the trigger/default work
        payload.pop("last_message_at")

        params = {"customer_ig_id": f"eq.{customer_ig_id}"}
        if payload["merchant_id"]:
            params["merchant_id"] = f"eq.{payload['merchant_id']}"

        try:
            existing = self.client.get(self.conversations_table, {**params, "select": "id"})
            if existing:
                conversation_uuid = existing[0]["id"]
                response = self.client.request(
                    "PATCH",
                    self.conversations_table,
                    json={k: v for k, v in payload.items() if k != "customer_ig_id"},
                    params={"id": f"eq.{conversation_uuid}"},
                    prefer="return=representation",
                )
            else:
                response = self.client.request(
                    "POST",
                    self.conversations_table,
                    json=payload,
                    prefer="return=representation",
                )
            if response.status_code >= 300:
                logger.error("Conversation persist failed: %s", response.text[:400])
                return None
            body = response.json()
            row = body[0] if isinstance(body, list) and body else body
            conversation_uuid = (row or {}).get("id") or (existing[0]["id"] if existing else None)
            state.db_conversation_id = conversation_uuid
            if conversation_uuid and user_message:
                self._append_message(conversation_uuid, "CUSTOMER", user_message)
            if conversation_uuid and bot_message:
                self._append_message(conversation_uuid, "BOT", bot_message)
            return conversation_uuid
        except httpx.HTTPError as error:
            logger.error("Conversation persist failed: %s", error)
            return None

    def list_messages(self, conversation_uuid: str) -> list:
        if not self.enabled or self.client is None:
            return []
        return self.client.get(
            self.messages_table,
            {
                "select": "*",
                "conversation_id": f"eq.{conversation_uuid}",
                "order": "created_at.asc",
            },
        )

    def set_bot_active(self, customer_ig_id: str, active: bool, merchant_id: Optional[str] = None) -> bool:
        if not self.enabled or self.client is None:
            return False
        params = {"customer_ig_id": f"eq.{customer_ig_id}"}
        if merchant_id and is_configured(merchant_id):
            params["merchant_id"] = f"eq.{merchant_id}"
        response = self.client.request(
            "PATCH",
            self.conversations_table,
            json={"is_bot_active": active},
            params=params,
        )
        return response.status_code < 300

    def _append_message(self, conversation_uuid: str, sender_type: str, text: str) -> None:
        assert self.client is not None
        try:
            self.client.request(
                "POST",
                self.messages_table,
                json={
                    "conversation_id": conversation_uuid,
                    "sender_type": sender_type,
                    "message_text": text,
                },
                prefer="return=minimal",
            )
        except httpx.HTTPError as error:
            logger.warning("Could not store message: %s", error)
