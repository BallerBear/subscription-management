from datetime import date

import pytest

from app.services.billing import _next_period


def test_monthly_billing_preserves_day_30() -> None:
    anchor = date(2026, 1, 30)

    assert _next_period(date(2026, 1, 30), "MONTHLY", anchor) == date(2026, 2, 28)
    assert _next_period(date(2026, 2, 28), "MONTHLY", anchor) == date(2026, 3, 30)
    assert _next_period(date(2026, 3, 30), "MONTHLY", anchor) == date(2026, 4, 30)


def test_monthly_billing_preserves_month_end() -> None:
    anchor = date(2026, 1, 31)

    assert _next_period(date(2026, 1, 31), "MONTHLY", anchor) == date(2026, 2, 28)
    assert _next_period(date(2026, 2, 28), "MONTHLY", anchor) == date(2026, 3, 31)


def test_yearly_billing_handles_leap_day() -> None:
    anchor = date(2024, 2, 29)

    assert _next_period(date(2024, 2, 29), "YEARLY", anchor) == date(2025, 2, 28)
    assert _next_period(date(2025, 2, 28), "YEARLY", anchor) == date(2026, 2, 28)
    assert _next_period(date(2027, 2, 28), "YEARLY", anchor) == date(2028, 2, 29)


def test_daily_and_weekly_billing() -> None:
    anchor = date(2026, 10, 31)

    assert _next_period(anchor, "DAILY", anchor) == date(2026, 11, 1)
    assert _next_period(anchor, "WEEKLY", anchor) == date(2026, 11, 7)


def test_unsupported_billing_period_raises() -> None:
    with pytest.raises(ValueError):
        _next_period(date(2026, 10, 31), "INVALID", date(2026, 10, 31))
