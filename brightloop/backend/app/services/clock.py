"""Time Machine: read, set and advance the system's 'today' (app_clock).

STUB: names, parameters and return shapes are final so routers and the UI can
build against them. Bodies are filled in by Person 1.
"""

from datetime import date


def get_clock() -> dict:
    """Return {"today": date}. Reads app_clock; no user needed."""
    raise NotImplementedError


def set_clock(user_id: int, today: date) -> dict:
    """Set app_clock.today to an exact date. Returns {"today": date}. Admin only (router)."""
    raise NotImplementedError


def advance_clock(user_id: int, days: int = 0, months: int = 0) -> dict:
    """Move 'today' forward by days and/or months. Returns {"today": date}.

    Months use Postgres interval maths so month ends clamp (Jan 31 + 1 month = Feb 28).
    """
    raise NotImplementedError
