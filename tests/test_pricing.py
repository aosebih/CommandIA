"""Backend pricing must override whatever totals the model invents."""
from tests.conftest import extraction_payload


def test_shipping_and_subtotal_come_from_catalog(make_service):
    service = make_service([
        extraction_payload(
            customer_name="Ahmed",
            wilaya_code=16,
            delivery_type="HOME",
            order_items=[{
                "product_name": "Brownie Classique",
                "quantity": 2,
                "unit_price_da": 1,
            }],
            subtotal_da=2,
            shipping_fee_da=1,
            total_price_da=3,
        )
    ])
    result = service.process_message(
        user_message="2 brownies Alger home",
        product_context={
            "name": "Brownie Classique",
            "price": 1550,
            "shipping_rates": {"16": {"HOME": 600, "DESK": 400}},
            "catalog": [{"name": "Brownie Classique", "price": 1550}],
        },
    )
    data = result["extracted_data"]
    assert data["subtotal_da"] == 3100
    assert data["shipping_fee_da"] == 600
    assert data["total_price_da"] == 3700


def test_desk_is_rejected_when_merchant_disables_it(make_service):
    service = make_service([
        extraction_payload(delivery_type="DESK", customer_name="Ahmed")
    ])
    result = service.process_message(
        user_message="stop desk",
        product_context={"allows_desk_delivery": False},
    )
    assert result["extracted_data"]["delivery_type"] is None
    assert "delivery_type" in result["missing_fields"]
