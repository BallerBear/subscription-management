from fastapi import APIRouter, Depends, Query, status

from app.core.deps import require_role
from app.core.errors import friendly_error
from app.schemas.billing import PaymentIn
from app.services import payments as service

router = APIRouter(tags=["payments"])
staff = require_role("ADMIN", "STAFF")


@router.post("/invoices/{invoice_id}/payments", status_code=status.HTTP_201_CREATED)
def record_payment(invoice_id: int, body: PaymentIn, user: dict = Depends(staff)):
    try:
        return service.record_payment(
            user["id"], invoice_id, body.method, body.amount, body.paid_on, body.reference, body.note
        )
    except ValueError as exc:  # e.g. paid_on is after the Time Machine's today
        raise friendly_error(str(exc), 400, "paid_on" if "date" in str(exc).lower() else None)


@router.get("/payments")
def list_payments(
    invoice_id: int | None = None,
    customer_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: dict = Depends(staff),
):
    return service.list_payments(page, page_size, invoice_id, customer_id)
