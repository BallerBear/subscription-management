from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ProductType = Literal["SOFTWARE", "ADD_ON", "SERVICE"]
BillingPeriod = Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]


class TaxCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    rate_bps: int = Field(ge=0, le=10000)


class TaxUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    rate_bps: int | None = Field(default=None, ge=0, le=10000)


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    type: ProductType
    sales_price: int = Field(ge=0)
    cost_price: int = Field(default=0, ge=0)
    notes: str | None = None
    tax_id: int = Field(gt=0)


class ProductUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: ProductType | None = None
    sales_price: int | None = Field(default=None, ge=0)
    cost_price: int | None = Field(default=None, ge=0)
    notes: str | None = None
    tax_id: int | None = Field(default=None, gt=0)


class VariantCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    attribute: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=150)
    extra_price: int = Field(default=0, ge=0)


class VariantUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    attribute: str | None = Field(default=None, min_length=1, max_length=100)
    value: str | None = Field(default=None, min_length=1, max_length=150)
    extra_price: int | None = Field(default=None, ge=0)


class PlanCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    price: int = Field(default=0, ge=0)
    billing_period: BillingPeriod
    min_quantity: int = Field(default=1, ge=1)
    available_from: date
    available_to: date | None = None
    tax_id: int | None = Field(default=None, gt=0)
    auto_close: bool = False
    allow_early_close: bool = True
    allow_pause: bool = False
    allow_renew: bool = True

    @model_validator(mode="after")
    def validate_plan(self):
        if self.available_to is not None and self.available_to < self.available_from:
            raise ValueError("Availability end date cannot be before its start date")
        if self.price > 0 and self.tax_id is None:
            raise ValueError("A tax rule is required when the plan has a fee")
        return self


class PlanUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    price: int | None = Field(default=None, ge=0)
    billing_period: BillingPeriod | None = None
    min_quantity: int | None = Field(default=None, ge=1)
    available_from: date | None = None
    available_to: date | None = None
    tax_id: int | None = Field(default=None, gt=0)
    auto_close: bool | None = None
    allow_early_close: bool | None = None
    allow_pause: bool | None = None
    allow_renew: bool | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.available_from is not None and self.available_to is not None and self.available_to < self.available_from:
            raise ValueError("Availability end date cannot be before its start date")
        return self
