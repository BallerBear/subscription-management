from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.deps import require_role
from app.schemas.billing import InvTransitionIn
from app.services import billing, invoices as service

router = APIRouter(prefix="/invoices", tags=["invoices"])
staff = require_role("ADMIN", "STAFF")


@router.get("")
def list_invoices(
    status: str | None = None,
    customer_id: int | None = None,
    overdue: bool = False,
    q: str | None = None,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: dict = Depends(staff),
):
    return service.list_invoices(status, customer_id, overdue, q, date_from, date_to, page, page_size)


# Fixed path first so "confirm-drafts" is never read as an {invoice_id}.
@router.post("/confirm-drafts")
def confirm_drafts(user: dict = Depends(staff)):
    return billing.confirm_all_drafts(user["id"])


@router.get("/{invoice_id}")
def get_invoice(invoice_id: int, _: dict = Depends(staff)):
    return service.get_invoice(invoice_id)


@router.post("/{invoice_id}/transition")
def transition(invoice_id: int, body: InvTransitionIn, user: dict = Depends(staff)):
    return service.transition_invoice(user["id"], invoice_id, body.to_status)


@router.post("/{invoice_id}/send")
def send(invoice_id: int, user: dict = Depends(staff)):
    return service.send_invoice(user["id"], invoice_id)
