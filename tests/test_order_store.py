"""Supabase persistence. The HTTP call is mocked, no network is used."""
import json

import httpx

from order_store import OrderStore

ORDER = {
    "order_id": "11111111-2222-3333-4444-555555555555",
    "customer_name": "Ahmed Benali",
    "phone_number": "0550123456",
    "wilaya": "Alger",
    "delivery_type": "HOME",
    "address": "Rue Didouche, Alger Centre",
    "product_details": {
        "item_id": "hoodie_001",
        "quantity": 1,
        "size_color": "L/Black",
    },
    "total_price_da": 4000.0,
    "order_status": "CONFIRMED",
}


def test_disabled_when_credentials_are_placeholders():
    store = OrderStore(url="your_supabase_url_here", key="your_supabase_key_here")
    assert store.enabled is False
    assert store.save_order(ORDER) is False


def test_disabled_without_credentials():
    store = OrderStore(url="", key="")
    assert store.enabled is False
    assert store.save_order(ORDER) is False


def test_save_order_posts_the_canonical_contract(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return httpx.Response(201)

    store = OrderStore(url="https://demo.supabase.co", key="secret-key")
    assert store.enabled is True

    transport = httpx.MockTransport(handler)
    original = httpx.post
    httpx.post = lambda url, **kwargs: httpx.Client(transport=transport).post(url, **kwargs)
    try:
        assert store.save_order(ORDER) is True
    finally:
        httpx.post = original

    assert captured["url"] == "https://demo.supabase.co/rest/v1/orders"
    assert captured["headers"]["apikey"] == "secret-key"
    assert captured["headers"]["authorization"] == "Bearer secret-key"
    assert captured["body"]["order_id"] == ORDER["order_id"]
    assert captured["body"]["product_details"]["item_id"] == "hoodie_001"
    assert captured["body"]["total_price_da"] == 4000.0
    assert captured["body"]["order_status"] == "CONFIRMED"


def test_save_order_survives_an_http_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    store = OrderStore(url="https://demo.supabase.co", key="secret-key")
    transport = httpx.MockTransport(handler)
    original = httpx.post
    httpx.post = lambda url, **kwargs: httpx.Client(transport=transport).post(url, **kwargs)
    try:
        assert store.save_order(ORDER) is False
    finally:
        httpx.post = original


def test_save_order_survives_a_network_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    store = OrderStore(url="https://demo.supabase.co", key="secret-key")
    transport = httpx.MockTransport(handler)
    original = httpx.post
    httpx.post = lambda url, **kwargs: httpx.Client(transport=transport).post(url, **kwargs)
    try:
        assert store.save_order(ORDER) is False
    finally:
        httpx.post = original
