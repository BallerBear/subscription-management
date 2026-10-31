import pytest


@pytest.mark.skip(reason="Billing idempotency behavior is not implemented yet")
def test_billing_operation_is_idempotent() -> None:
    raise NotImplementedError
