"""Request models for staff accounts and customers (Pydantic v2).

The same rules live in frontend/src/lib/validators.ts (Zod).
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+ -]{7,15}$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def _email(v: str) -> str:
    v = v.strip().lower()
    if not EMAIL_RE.match(v):
        raise ValueError("Entered email is invalid")
    return v


def _blank_to_none(v):
    return None if v is None or (isinstance(v, str) and not v.strip()) else v


class CustomerIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_name: str = Field(min_length=1, max_length=150)
    contact_name: str = Field(min_length=2, max_length=100)
    email: str
    phone: str | None = None
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    gstin: str | None = None

    @field_validator("email")
    @classmethod
    def _e(cls, v):
        return _email(v)

    @field_validator("phone", "address_line", "city", "state", "postal_code", "gstin", mode="before")
    @classmethod
    def _blank(cls, v):
        return _blank_to_none(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        if v is not None and not PHONE_RE.match(v):
            raise ValueError("Phone must be 7-15 digits (spaces, + and - allowed)")
        return v

    @field_validator("gstin")
    @classmethod
    def _gstin(cls, v):
        if v is not None:
            v = v.upper()
            if not GSTIN_RE.match(v):
                raise ValueError("GSTIN must look like 33AABCK1234F1Z5")
        return v


class CustomerPatch(CustomerIn):
    """Same rules, but every field is optional (send only what changed)."""

    company_name: str | None = Field(default=None, min_length=1, max_length=150)
    contact_name: str | None = Field(default=None, min_length=2, max_length=100)
    email: str | None = None  # type: ignore[assignment]
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def _e(cls, v):  # noqa: F811
        return _email(v) if v is not None else v
