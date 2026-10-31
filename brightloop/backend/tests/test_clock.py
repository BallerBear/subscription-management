from datetime import date

from app.services.clock import get_clock


def test_get_clock_returns_a_date() -> None:
    # Deliberately does NOT call close_pool(): the pool is shared by the whole
    # test session and psycopg_pool cannot be reopened once it is closed, so
    # closing it here would break every test that runs afterwards.
    result = get_clock()

    assert "today" in result
    assert isinstance(result["today"], date)
