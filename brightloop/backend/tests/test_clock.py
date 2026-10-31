from datetime import date

from app.core.db import close_pool
from app.services.clock import get_clock


def test_get_clock_returns_a_date() -> None:
    try:
        result = get_clock()

        assert "today" in result
        assert isinstance(result["today"], date)
    finally:
        close_pool()
