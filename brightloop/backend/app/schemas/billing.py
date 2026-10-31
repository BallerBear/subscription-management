"""Request models for subscriptions, invoices and payments (Pydantic v2)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class LineIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(ge=1, le=100000)


class SubscriptionIn(BaseModel):
    customer_id: int
    plan_id: int
    payment_term_id: int
    start_date: date
    expiry_date: date
    lines: list[LineIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _dates(self):
        if self.expiry_date <= self.start_date:
            raise ValueError("Expiry date must be after the start date")
        return self


SubStatus = Literal["DRAFT", "QUOTATION", "CONFIRMED", "ACTIVE", "PAUSED", "CLOSED"]
InvStatus = Literal["DRAFT", "CONFIRMED", "PAID", "CANCELLED"]


class SubTransitionIn(BaseModel):
    to_status: SubStatus


class InvTransitionIn(BaseModel):
    to_status: InvStatus


class DiscountAttachIn(BaseModel):
    discount_id: int


class PaymentIn(BaseModel):
    method: Literal["CARD", "UPI", "BANK_TRANSFER", "CASH", "CHEQUE"]
    amount: int = Field(gt=0, description="Paise")
    paid_on: date
    reference: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=300)

    @field_validator("reference", "note", mode="before")
    @classmethod
    def _blank(cls, v):
        return None if isinstance(v, str) and not v.strip() else v


class BillingRunIn(BaseModel):
    auto_confirm: bool = True
