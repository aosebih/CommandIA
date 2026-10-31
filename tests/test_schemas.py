"""Schema contracts and the shared phone normalizer."""
import pytest
from pydantic import ValidationError

from schemas import (
    OrderExtractionData,
    normalize_algerian_phone,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0550123456", "0550123456"),
        ("0550 12 34 56", "0550123456"),
        ("+213 550 12 34 56", "0550123456"),
        ("+213550123456", "0550123456"),
        ("00213 550 12 34 56", "0550123456"),
        ("0550-12-34-56", "0550123456"),
    ],
)
def test_normalize_valid_phone(raw, expected):
    assert normalize_algerian_phone(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["12345", "05501234", "0999999999", "abcdefghij", "", None, "+213 000 12 34 56"],
)
def test_normalize_invalid_phone(raw):
    assert normalize_algerian_phone(raw) is None


def test_order_requires_valid_phone():
    with pytest.raises(ValidationError):
        OrderExtractionData(customer_name="Ahmed", phone_number="12345")


def test_order_accepts_valid_phone():
    order = OrderExtractionData(customer_name="Ahmed", phone_number="+213 550 12 34 56")
    assert order.phone_number == "0550123456"


def test_order_rejects_out_of_range_wilaya():
    with pytest.raises(ValidationError):
        OrderExtractionData(customer_name="Ahmed", wilaya_code=99)
