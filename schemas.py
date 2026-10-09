"""
Pydantic schemas for CommandIA order extraction.
Defines the 5 Sacred Fields and full order structure as per PRD/Roadmap.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


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
    subtotal_da: Optional[float] = Field(default=None)
    shipping_fee_da: Optional[float] = Field(default=None)
    total_price_da: Optional[float] = Field(default=None)
    order_status: OrderStatus = Field(default=OrderStatus.PENDING_CONFIRMATION)
