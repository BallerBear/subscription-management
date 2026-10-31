"""Password reset rules that need no database. The full flow is checked by hand against Mailpit."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.services.password_reset import _hash


def test_token_is_stored_as_a_sha256_hash_not_the_raw_token():
    digest = _hash("some-token-value")
    assert digest != "some-token-value"
    assert len(digest) == 64
    assert digest == _hash("some-token-value")  # deterministic, so lookup by hash works


def test_forgot_password_normalises_and_validates_email():
    assert ForgotPasswordRequest(email="  Ana@Example.COM ").email == "ana@example.com"
    with pytest.raises(ValidationError):
        ForgotPasswordRequest(email="not-an-email")


@pytest.mark.parametrize("bad", ["Short1!", "alllowercase1!", "ALLUPPERCASE1!", "NoSpecial1234"])
def test_reset_password_enforces_the_signup_password_rules(bad):
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token="x" * 43, password=bad)


def test_reset_password_accepts_a_strong_password():
    assert ResetPasswordRequest(token="x" * 43, password="Newpass!456").password == "Newpass!456"
