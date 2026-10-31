import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_email(value: str) -> str:
    value = value.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise ValueError("Enter a valid email address")
    return value


def _validate_password(value: str) -> str:
    if len(value) <= 8:
        raise ValueError("Password must be longer than eight characters")
    if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must contain uppercase, lowercase and a special character")
    if len(value) > 72:
        raise ValueError("Password must be no longer than 72 characters")
    return value


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: str = Field(min_length=3, max_length=254)
    password: str
    name: str = Field(min_length=1, max_length=120)
    company_name: str = Field(min_length=1, max_length=200)
    contact_name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=15)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _validate_email(value)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _validate_password(value)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[0-9+ -]{7,15}", value):
            raise ValueError("Enter a valid phone number")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class StaffCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str
    name: str = Field(min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _validate_email(value)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _validate_password(value)


class BootstrapAdminRequest(BaseModel):
    bootstrap_token: str = Field(min_length=1)
    email: str = Field(min_length=3, max_length=254)
    password: str
    name: str = Field(min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _validate_email(value)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _validate_password(value)
