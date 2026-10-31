from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest
from app.schemas.catalog import PlanCreate, ProductCreate, TaxCreate, VariantCreate


def test_registration_requires_strong_password():
    base = {
        "email": "owner@example.com",
        "name": "Owner",
        "company_name": "Example Ltd",
        "contact_name": "Owner",
    }
    with pytest.raises(ValidationError):
        RegisterRequest(**base, password="weakpassword")
    with pytest.raises(ValidationError):
        RegisterRequest(**base, password="Short1!")
    assert RegisterRequest(**base, password="StrongPass1!").email == "owner@example.com"


def test_tax_rate_is_basis_points():
    assert TaxCreate(name="GST 18%", rate_bps=1800).rate_bps == 1800
    with pytest.raises(ValidationError):
        TaxCreate(name="GST", rate_bps=10001)


def test_product_prices_are_non_negative_integer_minor_units():
    product = ProductCreate(
        name="Business Suite",
        type="SOFTWARE",
        sales_price=256000,
        cost_price=100000,
        tax_id=1,
    )
    assert product.sales_price == 256000
    with pytest.raises(ValidationError):
        ProductCreate(name="Bad", type="SOFTWARE", sales_price=-1, tax_id=1)


def test_variant_extra_price_is_non_negative():
    assert VariantCreate(attribute="Brand", value="Odoo", extra_price=56000).extra_price == 56000
    with pytest.raises(ValidationError):
        VariantCreate(attribute="Brand", value="Odoo", extra_price=-1)


def test_plan_requires_tax_when_fee_is_nonzero():
    values = {
        "name": "Business Monthly",
        "price": 500000,
        "billing_period": "MONTHLY",
        "available_from": date(2026, 1, 1),
    }
    with pytest.raises(ValidationError):
        PlanCreate(**values)
    assert PlanCreate(**values, tax_id=1).tax_id == 1


def test_plan_dates_must_be_ordered():
    with pytest.raises(ValidationError):
        PlanCreate(
            name="Expired",
            billing_period="YEARLY",
            available_from=date(2026, 2, 1),
            available_to=date(2026, 1, 1),
        )
