from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.deps import require_role
from app.core.errors import friendly_error
from app.services import reports as service

router = APIRouter(prefix="/reports", tags=["reports"])
staff = require_role("ADMIN", "STAFF")


@router.get("/kpis")
def kpis(_: dict = Depends(staff)):
    return service.get_kpis()


@router.get("/monthly-collections")
def monthly(
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    _: dict = Depends(staff),
):
    try:
        return service.monthly_collections(date_from, date_to)
    except ValueError as exc:
        raise friendly_error(str(exc), 400)


@router.get("/overdue")
def overdue(
    customer_id: int | None = None,
    plan_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: dict = Depends(staff),
):
    return service.overdue_invoices(page, page_size, customer_id, plan_id)
