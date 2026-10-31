"""
Shared pytest fixtures.

Every test in this suite runs fully offline: the Gemini client is replaced by
a deterministic stub, so the suite never consumes API quota and never fails
because of a provider outage.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The AI module refuses to start without a key. Load the real .env first so
# the opt-in golden dataset can reach the API, and only fall back to a dummy
# value when no key is configured. dotenv does not override variables that
# are already set, so an explicit shell variable still wins.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:  # pragma: no cover - dotenv is a runtime dependency
    pass

os.environ.setdefault("GEMINI_API_KEY", "test-key-offline")


class StubResponse:
    def __init__(self, text: str):
        self.text = text


class StubModels:
    """Returns queued payloads instead of calling Gemini."""

    def __init__(self, payloads: List[Dict[str, Any]]):
        self._payloads = list(payloads)
        self.calls: List[Dict[str, Any]] = []

    def generate_content(self, model=None, contents=None, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if not self._payloads:
            raise AssertionError("StubModels ran out of queued payloads")
        payload = self._payloads.pop(0)
        return StubResponse(json.dumps(payload))


class StubClient:
    def __init__(self, payloads: List[Dict[str, Any]]):
        self.models = StubModels(payloads)


def extraction_payload(
    reply: str = "ok",
    customer_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    wilaya_code: Optional[int] = None,
    delivery_type: Optional[str] = None,
    address: Optional[str] = None,
    order_items: Optional[List[Dict[str, Any]]] = None,
    subtotal_da: Optional[float] = None,
    shipping_fee_da: Optional[float] = None,
    total_price_da: Optional[float] = None,
    order_status: str = "PENDING_CONFIRMATION",
) -> Dict[str, Any]:
    """Build a raw Gemini-shaped extraction payload."""
    return {
        "reply_to_customer": reply,
        "extracted_data": {
            "customer_name": customer_name,
            "phone_number": phone_number,
            "wilaya_code": wilaya_code,
            "delivery_type": delivery_type,
            "address": address,
            "order_items": order_items or [],
            "subtotal_da": subtotal_da,
            "shipping_fee_da": shipping_fee_da,
            "total_price_da": total_price_da,
            "order_status": order_status,
        },
    }


def make_brain(payloads: List[Dict[str, Any]]):
    """Build an AIBrain wired to the stub client."""
    from ai_brain import AIBrain

    brain = AIBrain.__new__(AIBrain)
    brain.api_key = "test-key-offline"
    brain.model = "gemini-3.5-flash-lite"
    brain.models = ["gemini-3.5-flash-lite", "gemini-3.5-flash"]
    brain.system_prompt = "SYSTEM"
    brain.client = StubClient(payloads)
    return brain


@pytest.fixture
def make_service():
    """Factory returning an AIService backed by the stub client."""
    from ai_service import AIService

    def factory(payloads: List[Dict[str, Any]]):
        service = AIService.__new__(AIService)
        service.brain = make_brain(payloads)
        service._conversations = {}
        return service

    return factory


@pytest.fixture
def brain():
    return make_brain([])
