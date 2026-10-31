from datetime import date

import pytest

from app.services.reports import monthly_collections, overdue_invoices


def test_monthly_collections_rejects_reversed_dates():
    with pytest.raises(ValueError, match="date_from cannot be after date_to"):
        monthly_collections(
            date_from=date(2026, 11, 1),
            date_to=date(2026, 10, 1),
        )


@pytest.mark.parametrize("page,page_size", [(0, 25), (-1, 25), (1, 0), (1, 101)])
def test_overdue_invoices_rejects_invalid_pagination(page, page_size):
    with pytest.raises(ValueError):
        overdue_invoices(page=page, page_size=page_size)
