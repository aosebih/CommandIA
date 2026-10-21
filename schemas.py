"""
Pydantic schemas for CommandIA order extraction.
Defines the 5 Sacred Fields and full order structure as per PRD/Roadmap.
"""
from enum import Enum
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from wilayas import get_wilaya_name


ALGERIAN_PHONE_PATTERN = re.compile(r"^0[567]\d{8}$")


def normalize_algerian_phone(value: Optional[str]) -> Optional[str]:
    """
    Normalize an Algerian phone number to its 10-digit form.

    Accepts the formats customers actually type: "0550123456",
    "05 50 12 34 56", "+213 550 12 34 56" and "00213550123456".
    Returns None when the value cannot be a valid Algerian mobile number.
    """
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    if digits.startswith("00213"):
        digits = digits[5:]
    elif digits.startswith("213"):
        digits = digits[3:]
    if len(digits) == 9 and digits[0] in "567":
        digits = "0" + digits
    if not ALGERIAN_PHONE_PATTERN.match(digits):
        return None
    return digits


class DeliveryType(str, Enum):
    """Delivery type options."""
    HOME = "HOME"
    DESK = "DESK"  # Stop-desk / point relais / bureau


class OrderStatus(str, Enum):
    """Order status states."""
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"


class OrderItem(BaseModel):
    """Individual order item."""
    product_name: str = Field(..., description="Product name")
    quantity: int = Field(..., ge=1, description="Quantity of items")
    size_color: Optional[str] = Field(default=None, description="Size and/or color specification")
    unit_price_da: Optional[float] = Field(default=None, ge=0, description="Unit price in Algerian Dinars")


class OrderExtractionData(BaseModel):
    """Extracted order data."""
    customer_name: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)
    wilaya_code: Optional[int] = Field(default=None, ge=1, le=69)
    delivery_type: Optional[DeliveryType] = Field(default=None)
    address: Optional[str] = Field(default=None)
    order_items: list[OrderItem] = Field(default_factory=list)
    subtotal_da: Optional[float] = Field(default=None, ge=0)
    shipping_fee_da: Optional[float] = Field(default=None, ge=0)
    total_price_da: Optional[float] = Field(default=None, ge=0)
    order_status: OrderStatus = Field(default=OrderStatus.PENDING_CONFIRMATION)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = normalize_algerian_phone(value)
        if normalized is None:
            raise ValueError("phone_number must be a valid 10-digit Algerian number")
        return normalized

    @field_validator("wilaya_code")
    @classmethod
    def validate_wilaya_code(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and get_wilaya_name(value) is None:
            raise ValueError("wilaya_code must identify a supported Algerian wilaya")
        return value


class OrderExtractionResponse(BaseModel):
    """Full extraction response."""
    reply_to_customer: str = Field(...)
    extracted_data: OrderExtractionData = Field(...)


class Order(BaseModel):
    """Complete order structure."""
    order_id: str = Field(..., description="UUID v4 for the order")
    customer_name: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)
    wilaya_code: Optional[int] = Field(default=None)
    delivery_type: Optional[DeliveryType] = Field(default=None)
    address: Optional[str] = Field(default=None)
    order_items: list[OrderItem] = Field(default_factory=list)
    subtotal_da: Optional[float] = Field(default=None, ge=0)
    shipping_fee_da: Optional[float] = Field(default=None, ge=0)
    total_price_da: Optional[float] = Field(default=None, ge=0)
    order_status: OrderStatus = Field(default=OrderStatus.PENDING_CONFIRMATION)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = normalize_algerian_phone(value)
        if normalized is None:
            raise ValueError("phone_number must be a valid 10-digit Algerian number")
        return normalized

    @field_validator("wilaya_code")
    @classmethod
    def validate_wilaya_code(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and get_wilaya_name(value) is None:
            raise ValueError("wilaya_code must identify a supported Algerian wilaya")
        return value

