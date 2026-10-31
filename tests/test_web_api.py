"""End-to-end tests for the local /api routes used by the React frontend."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api_routes
import app as app_module
from local_store import LocalStore

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path, monkeypatch):
    previous = api_routes.store
    api_routes.store = LocalStore(tmp_path / "state.json", ROOT / "data" / "seed.json")

    def offline_ai():
        raise RuntimeError("GEMINI_API_KEY not configured for this test")

    monkeypatch.setattr(app_module, "get_ai_service", offline_ai)
    with TestClient(app_module.app) as test_client:
        yield test_client
    api_routes.store = previous


def sign_in(client):
    response = client.post(
        "/api/auth/sign-in",
        json={"email": "demo@commandia.dz", "password": "demo1234"},
    )
    assert response.status_code == 200
    return response.json()


def test_api_requires_authentication(client):
    assert client.get("/api/conversations").status_code == 401
    assert client.get("/api/orders").status_code == 401
    assert client.get("/api/products").status_code == 401


def test_demo_sign_in_and_sign_out(client):
    user = sign_in(client)
    assert user == {"name": "Demo User", "email": "demo@commandia.dz"}
    assert client.get("/api/auth/me").json() == user
    assert client.get("/api/conversations").status_code == 200

    assert client.post("/api/auth/sign-out").json() == {"ok": True}
    assert client.get("/api/conversations").status_code == 401


def test_sign_up_rejects_duplicates(client):
    payload = {"name": "New Owner", "email": "owner@example.dz", "password": "secret12"}
    created = client.post("/api/auth/sign-up", json=payload)
    assert created.status_code == 200
    assert created.json()["email"] == "owner@example.dz"

    client.post("/api/auth/sign-out")
    duplicate = client.post("/api/auth/sign-up", json=payload)
    assert duplicate.status_code == 409

    bad_login = client.post(
        "/api/auth/sign-in",
        json={"email": "owner@example.dz", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401


def test_ai_message_falls_back_offline_and_manual_mode_stays_silent(client):
    sign_in(client)
    conversations = client.get("/api/conversations").json()
    target = next(item for item in conversations if item["m"] == "ai")

    response = client.post(
        f"/api/conversations/{target['id']}/messages",
        json={"text": "prix black sneakers"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message"]["w"] == "h"
    assert body["reply"]["w"] == "a"
    assert "6,800 DA" in body["reply"]["t"]
    assert body["intent"] == "Product inquiry"

    assert client.patch(
        f"/api/conversations/{target['id']}/mode",
        json={"mode": "manual"},
    ).json() == "manual"
    silent = client.post(
        f"/api/conversations/{target['id']}/messages",
        json={"text": "Another message"},
    )
    assert silent.status_code == 200
    assert silent.json()["reply"] is None


def test_ai_order_extraction_creates_an_awaiting_order(client, monkeypatch):
    sign_in(client)
    target = next(item for item in client.get("/api/conversations").json() if item["m"] == "ai")

    def fake_ai(conversation, text):
        return {
            "reply_to_customer": "Merci, votre commande est notee.",
            "state": "CONFIRMATION",
            "extracted_data": {
                "customer_name": "Nadia Test",
                "phone_number": "0550112233",
                "wilaya_code": 16,
                "delivery_type": "HOME",
                "address": "1 Rue de Test, Alger",
                "order_items": [
                    {"product_name": "Black sneakers", "quantity": 1, "unit_price_da": 6800}
                ],
                "subtotal_da": 6800,
                "shipping_fee_da": 600,
                "total_price_da": 7400,
                "order_status": "PENDING_CONFIRMATION",
            },
            "order_data": {"wilaya": "Alger"},
        }

    monkeypatch.setattr(api_routes, "_ai_result", fake_ai)
    response = client.post(
        f"/api/conversations/{target['id']}/messages",
        json={"text": "Je confirme"},
    )
    assert response.status_code == 200

    order = next(
        item for item in client.get("/api/orders").json()
        if item.get("conversationId") == target["id"]
    )
    assert order["name"] == "Nadia Test"
    assert order["ph"] == "0550112233"
    assert order["wil"] == "Alger"
    assert order["del"] == "Home delivery"
    assert order["tot"] == 7400
    # Orders are never auto-confirmed, even when the model says CONFIRMED.
    assert order["st"] == "await"


def test_products_orders_settings_and_rules(client):
    sign_in(client)

    product = client.post("/api/products", json={"n": "Test product", "p": 1000, "s": 3})
    assert product.status_code == 200
    product_id = product.json()["id"]
    updated = client.put(
        f"/api/products/{product_id}",
        json={"n": "Test product", "p": 1200, "s": 2},
    )
    assert updated.json()["p"] == 1200

    order = client.get("/api/orders").json()[0]
    status = client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "shipped"},
    )
    assert status.json() == "shipped"

    assert client.patch("/api/settings/ai", json={"enabled": False}).json()["ai"] is False
    assert client.post("/api/integrations/instagram/connect").json()["ig"] is True
    assert client.post("/api/integrations/instagram/disconnect").json()["ig"] is False

    rules = client.get("/api/rules").json()
    rules["opens"] = "08:30"
    saved = client.put("/api/rules", json=rules)
    assert saved.status_code == 200
    assert saved.json()["opens"] == "08:30"


def test_unknown_api_route_is_not_the_spa(client):
    assert client.get("/api/does-not-exist").status_code == 404
