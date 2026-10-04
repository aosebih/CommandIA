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


class ProductDetails(BaseModel):
    """Product details for the order."""
    item_id: str = Field(..., description="Product/item identifier")
    quantity: int = Field(..., ge=1, description="Quantity of items")
    size_color: str = Field(..., description="Size and/or color specification")


class OrderExtraction(BaseModel):
    """
    The 5 Sacred Fields schema for AI extraction.
    These fields must be collected before confirming an order (PRD 3.2).
    """
    # Field 1: Full Name
    customer_name: str = Field(
        ...,
        min_length=2,
        description="Full name (must contain at least a first name)"
    )
    
    # Field 2: Phone Number - Algerian format
    phone_number: str = Field(
        ...,
        description="Algerian phone number starting with 05, 06, or 07 (10 digits total)"
    )
    
    # Field 3: Wilaya - Algerian province
    wilaya: str = Field(
        ...,
        description="Algerian Wilaya (must match one of the 58 official Wilayas)"
    )
    
    # Field 4: Delivery Type
    delivery_type: DeliveryType = Field(
        ...,
        description="Delivery type: HOME (domicile) or DESK (point relais/bureau)"
    )
    
    # Field 5: Address
    address: str = Field(
        ...,
        min_length=3,
        description="Delivery address: Commune/street for HOME, or location for DESK"
    )
    
    @field_validator("phone_number")
    @classmethod
    def validate_algerian_phone(cls, v: str) -> str:
        """
        Validate Algerian phone number format.
        Must start with 05, 06, or 07 and be exactly 10 digits.
        """
        # Remove spaces, dashes, or other separators
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        # Check format: starts with 05,06,07 and has 10 digits total
        if not re.match(r"^(05|06|07)\d{8}$", cleaned):
            raise ValueError(
                "Invalid Algerian phone number. Must start with 05, 06, or 07 and be 10 digits total."
            )
        return cleaned


class Order(BaseModel):
    """
    Complete order structure matching the exact JSON schema from roadmap.
    """
    order_id: str = Field(..., description="UUID v4 for the order")
    customer_name: str = Field(...)
    phone_number: str = Field(...)
    wilaya: str = Field(...)
    delivery_type: DeliveryType = Field(...)
    address: str = Field(...)
    product_details: ProductDetails = Field(...)
    total_price_da: float = Field(ge=0, description="Total price in Algerian Dinars")
    order_status: OrderStatus = Field(default=OrderStatus.PENDING_CONFIRMATION)
    
    @field_validator("phone_number")
    @classmethod
    def validate_algerian_phone(cls, v: str) -> str:
        """Validate Algerian phone number format."""
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(05|06|07)\d{8}$", cleaned):
            raise ValueError(
                "Invalid Algerian phone number. Must start with 05, 06, or 07 and be 10 digits total."
            )
        return cleaned
