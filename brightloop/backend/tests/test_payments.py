from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.services.payments import record_payment, list_payments


@pytest.mark.parametrize("amount", [0, -1, -100])
def test_record_payment_rejects_nonpositive_amount(amount):
    with pytest.raises(ValueError, match="greater than zero"):
        record_payment(1, 1, "UPI", amount, date(2026, 10, 31))


def test_record_payment_rejects_invalid_method():
    with pytest.raises(ValueError, match="Invalid payment method"):
        record_payment(1, 1, "BITCOIN", 10000, date(2026, 10, 31))


def test_record_payment_rejects_future_date():
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = {
        "today": date(2026, 10, 31)
    }

    with patch("app.services.payments.transaction") as mock_transaction:
        mock_transaction.return_value.__enter__.return_value = mock_conn

        with pytest.raises(ValueError, match="cannot be after today"):
            record_payment(1, 1, "UPI", 10000, date(2026, 11, 1))


@pytest.mark.parametrize("page,page_size", [(0, 25), (1, 0), (1, 101), (-1, 25)])
def test_list_payments_rejects_invalid_pagination(page, page_size):
    with pytest.raises(ValueError):
        list_payments(page=page, page_size=page_size)


def test_payment_methods_are_valid():
    from app.services.payments import PAYMENT_METHODS

    assert PAYMENT_METHODS == {
        "CARD", "UPI", "BANK_TRANSFER", "CASH", "CHEQUE"
    }
