"""Billing engine: turns due ACTIVE subscriptions into invoices.

STUB: signature and return shape are final (CLAUDE.md section 8.3). Person 1
fills in the body: set-based SQL, one transaction, rounds until nothing is due.
"""


def run_billing(user_id: int, auto_confirm: bool = True) -> dict:
    """Bill every subscription that is due as of app_clock.today.

    Takes NO date argument on purpose: 'today' always comes from app_clock, so
    the Time Machine controls billing. Safe to run twice: the second run finds
    nothing due and creates nothing.

    Returns {"created": int, "skipped": int, "closed": int,
             "up_to_date": int, "as_of": date}
    """
    raise NotImplementedError


def confirm_all_drafts(user_id: int) -> dict:
    """Confirm every DRAFT invoice with one UPDATE. Returns {"confirmed": int}."""
    raise NotImplementedError
