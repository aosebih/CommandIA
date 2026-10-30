"""Supabase persistence. The HTTP call is mocked, no network is used."""
import json

import httpx

from backend.order_store import ORDER_COLUMNS, DERIVED_COLUMNS, OrderStore, sacred_fields_complete

ORDER = {
    "order_id": "11111111-2222-3333-4444-555555555555",
    "merchant_id": "11111111-1111-1111-1111-111111111111",
    "customer_name": "Ahmed Benali",
    "phone_number": "0550123456",
    "wilaya_code": 16,
    "delivery_type": "HOME",
    "address": "Rue Didouche, Alger Centre",
    "order_items": [
        {
            "product_name": "hoodie_001",
            "quantity": 1,
            "size_color": "L/Black",
            "unit_price_da": 4000.0,
        }
    ],
    "subtotal_da": 4000.0,
    "shipping_fee_da": 0.0,
    "total_price_da": 4000.0,
    "order_status": "CONFIRMED",
}


def _install(handler):
    transport = httpx.MockTransport(handler)
    original = httpx.request

    def wrapped(method, url, **kwargs):
        return httpx.Client(transport=transport).request(method, url, **kwargs)

    httpx.request = wrapped
    return original


def test_disabled_when_credentials_are_placeholders():
    store = OrderStore(url="your_supabase_url_here", key="your_supabase_key_here")
    assert store.enabled is False
    assert store.save_order(ORDER) is False


def test_disabled_without_credentials():
    store = OrderStore(url="", key="")
    assert store.enabled is False
    assert store.save_order(ORDER) is False


def test_save_order_posts_orders_and_items():
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append({
            "method": request.method,
            "url": str(request.url),
            "body": json.loads(request.content) if request.content else None,
        })
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(201, json=[{}])

    original = _install(handler)
    store = OrderStore(url="https://demo.supabase.co", key="secret-key")
    try:
        assert store.save_order(ORDER) is True
    finally:
        httpx.request = original

    methods = [item["method"] for item in captured]
    assert "POST" in methods
    assert captured[0]["url"].startswith("https://demo.supabase.co/rest/v1/orders")
    assert captured[0]["body"]["order_id"] == ORDER["order_id"]
    assert captured[0]["body"]["wilaya_code"] == 16
    assert captured[0]["body"]["wilaya_name"] == "Alger"
    assert captured[0]["body"]["order_status"] == "CONFIRMED"
    item_post = next(item for item in captured if "order_items" in item["url"] and item["method"] == "POST")
    assert item_post["body"][0]["extracted_product_name"] == "hoodie_001"


def test_save_order_survives_an_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    original = _install(handler)
    store = OrderStore(url="https://demo.supabase.co", key="secret-key")
    try:
        assert store.save_order(ORDER) is False
    finally:
        httpx.request = original


def test_save_order_survives_a_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    original = _install(handler)
    store = OrderStore(url="https://demo.supabase.co", key="secret-key")
    try:
        assert store.save_order(ORDER) is False
    finally:
        httpx.request = original


def test_sacred_fields_helper():
    assert sacred_fields_complete({
        "customer_name": "A",
        "phone_number": "0550123456",
        "wilaya_code": 16,
        "delivery_type": "HOME",
        "address": "x",
    })
    assert not sacred_fields_complete({"customer_name": "A"})


def test_contract_columns_are_exported():
    assert "order_id" in ORDER_COLUMNS
    assert "wilaya_name" in DERIVED_COLUMNS
