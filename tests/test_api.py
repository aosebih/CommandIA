"""HTTP service tests. Fully offline: the AI and the Graph API are stubbed."""
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

import app as app_module  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    # The configuration is read at import time, so the credentials are
    # injected on the module itself rather than through the environment.
    monkeypatch.setattr(app_module, "META_VERIFY_TOKEN", "test-verify-token")
    monkeypatch.setattr(app_module, "META_APP_SECRET", "test-app-secret")
    monkeypatch.setattr(app_module, "COMMANDIA_API_KEY", "test-api-key")
    app_module._ai_service = None
    app_module._ai_service_error = None
    app_module._seen_message_ids.clear()
    app_module._seen_message_ids_order.clear()
    with TestClient(app_module.app) as test_client:
        yield test_client


def sign(body: bytes, secret: str = "test-app-secret") -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def meta_payload(text: str, mid: str = "mid-1") -> dict:
    return {
        "object": "instagram",
        "entry": [
            {
                "id": "page-1",
                "time": 1700000000,
                "messaging": [
                    {
                        "sender": {"id": "sender-1"},
                        "recipient": {"id": "page-1"},
                        "timestamp": 1700000000,
                        "message": {"mid": mid, "text": text},
                    }
                ],
            }
        ],
    }


def test_healthz_is_public(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "ai_error" in body


def test_webhook_verification_success(client):
    response = client.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "test-verify-token",
        "hub.challenge": "1234567890",
    })
    assert response.status_code == 200
    assert response.text == "1234567890"


def test_webhook_verification_wrong_token(client):
    response = client.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong",
        "hub.challenge": "1234567890",
    })
    assert response.status_code == 403


def test_webhook_verification_bad_mode(client):
    response = client.get("/webhook", params={"hub.mode": "unsubscribe"})
    assert response.status_code == 400


def test_webhook_rejects_invalid_signature(client):
    body = json.dumps(meta_payload("Rani bghit nchri")).encode()
    response = client.post("/webhook", content=body, headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": "sha256=deadbeef",
    })
    assert response.status_code == 403


def test_webhook_rejects_missing_signature(client):
    body = json.dumps(meta_payload("Rani bghit nchri")).encode()
    response = client.post("/webhook", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 403


def test_webhook_processes_message_and_answers(client, monkeypatch):
    sent = {}

    class FakeService:
        def process_message(self, user_message, conversation_id=None, product_context=None):
            sent["message"] = user_message
            return {
                "reply_to_customer": "Salam! 3tini Ismouka",
                "language": "franco_arabic",
                "state": "ORDER_INTENT",
                "missing_fields": ["customer_name"],
                "collected_fields": {},
                "extracted_data": {"order_status": "PENDING_CONFIRMATION"},
                "order_data": {},
                "conversation_id": "conv-1",
                "error": None,
            }

    monkeypatch.setattr(app_module, "get_ai_service", lambda: FakeService())
    monkeypatch.setattr(app_module, "_send_meta_message",
                        lambda recipient, text: sent.update({"recipient": recipient, "text": text}) or True)

    body = json.dumps(meta_payload("Rani bghit nchri")).encode()
    response = client.post("/webhook", content=body, headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": sign(body),
    })
    assert response.status_code == 200
    assert response.json()["received"] == 1
    assert sent["message"] == "Rani bghit nchri"
    assert sent["recipient"] == "sender-1"
    assert sent["text"] == "Salam! 3tini Ismouka"


def test_webhook_deduplicates_message_ids(client, monkeypatch):
    calls = []

    class FakeService:
        def process_message(self, user_message, conversation_id=None, product_context=None):
            calls.append(user_message)
            return {"reply_to_customer": "ok", "extracted_data": {}, "order_data": {},
                    "error": None}

    monkeypatch.setattr(app_module, "get_ai_service", lambda: FakeService())
    monkeypatch.setattr(app_module, "_send_meta_message", lambda recipient, text: True)

    body = json.dumps(meta_payload("Rani bghit nchri", mid="same-mid")).encode()
    headers = {"Content-Type": "application/json", "X-Hub-Signature-256": sign(body)}

    first = client.post("/webhook", content=body, headers=headers)
    second = client.post("/webhook", content=body, headers=headers)

    assert first.json()["received"] == 1
    assert second.json()["received"] == 0
    assert len(calls) == 1


def test_webhook_ignores_echo_and_empty_text(client, monkeypatch):
    calls = []

    class FakeService:
        def process_message(self, user_message, conversation_id=None, product_context=None):
            calls.append(user_message)
            return {"reply_to_customer": "ok", "extracted_data": {}, "order_data": {},
                    "error": None}

    monkeypatch.setattr(app_module, "get_ai_service", lambda: FakeService())
    monkeypatch.setattr(app_module, "_send_meta_message", lambda recipient, text: True)

    payload = meta_payload("Rani bghit nchri")
    payload["entry"][0]["messaging"].append({
        "sender": {"id": "page-1"},
        "recipient": {"id": "sender-1"},
        "message": {"mid": "echo-1", "text": "Rani bghit nchri", "is_echo": True},
    })
    payload["entry"][0]["messaging"].append({
        "sender": {"id": "sender-2"},
        "recipient": {"id": "page-1"},
        "message": {"mid": "empty-1", "text": "   "},
    })

    body = json.dumps(payload).encode()
    response = client.post("/webhook", content=body, headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": sign(body),
    })
    assert response.status_code == 200
    assert response.json()["received"] == 1
    assert len(calls) == 1


def test_chat_requires_api_key(client):
    response = client.post("/chat", json={"message": "Rani bghit nchri"})
    assert response.status_code == 401


def test_chat_rejects_wrong_api_key(client):
    response = client.post("/chat", json={"message": "Rani bghit nchri"},
                           headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_chat_returns_result(client, monkeypatch):
    class FakeService:
        def process_message(self, user_message, conversation_id=None, product_context=None):
            return {
                "reply_to_customer": "Salam!",
                "language": "franco_arabic",
                "state": "ORDER_INTENT",
                "missing_fields": ["customer_name"],
                "collected_fields": {},
                "extracted_data": {"order_status": "PENDING_CONFIRMATION"},
                "order_data": {"order_id": "x"},
                "conversation_id": "conv-1",
                "error": None,
            }

    monkeypatch.setattr(app_module, "get_ai_service", lambda: FakeService())
    response = client.post("/chat", json={"message": "Rani bghit nchri"},
                           headers={"X-API-Key": "test-api-key"})
    assert response.status_code == 200
    body = response.json()
    assert body["reply_to_customer"] == "Salam!"
    assert body["language"] == "franco_arabic"
    assert body["error"] is None
