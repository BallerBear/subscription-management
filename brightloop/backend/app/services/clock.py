"""Time Machine: read, set and advance the system's 'today' (app_clock)."""

from datetime import date

from app.core.db import connection, transaction


def get_clock() -> dict:
    """Return {"today": date}. Reads app_clock; no user needed."""
    with connection() as conn:
        row = conn.execute(
            "SELECT today FROM app_clock WHERE singleton = TRUE"
        ).fetchone()

    if row is None:
        raise RuntimeError("The app_clock singleton row is missing")

    return {"today": row["today"]}


def set_clock(user_id: int, today: date) -> dict:
    """Set app_clock.today to an exact date. Returns {"today": date}."""
    with transaction(user_id=user_id) as conn:
        row = conn.execute(
            """
            UPDATE app_clock
            SET today = %s
            WHERE singleton = TRUE
            RETURNING today
            """,
            (today,),
        ).fetchone()

    if row is None:
        raise RuntimeError("The app_clock singleton row is missing")

    return {"today": row["today"]}


def advance_clock(
    user_id: int,
    days: int = 0,
    months: int = 0,
) -> dict:
    """Advance the clock using PostgreSQL calendar arithmetic.

    Month arithmetic clamps to the last valid day of the target month,
    e.g. January 31 + 1 month = February 28 (or 29 in a leap year).
    """
    if days < 0 or months < 0:
        raise ValueError("days and months must be non-negative")

    with transaction(user_id=user_id) as conn:
        row = conn.execute(
            """
            UPDATE app_clock
            SET today = (today + make_interval(days => %s, months => %s))::date
            WHERE singleton = TRUE
            RETURNING today
            """,
            (days, months),
        ).fetchone()

    if row is None:
        raise RuntimeError("The app_clock singleton row is missing")

    return {"today": row["today"]}