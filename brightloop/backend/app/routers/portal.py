"""Customer portal. customer_id ALWAYS comes from the logged-in user, never from the URL,
so editing an id in the address bar can only ever produce a 404 for someone else's record."""

from fastapi import APIRouter, Depends, Query

from app.core.deps import require_role
from app.services import invoices, people, portal, subscriptions

router = APIRouter(prefix="/portal", tags=["portal"])


def current_customer(user: dict = Depends(require_role("CUSTOMER"))) -> dict:
    return people.customer_for_user(user["id"])


@router.get("/summary")
def summary(me: dict = Depends(current_customer)):
    return portal.portal_summary(me["id"])


@router.get("/subscriptions")
def my_subscriptions(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    me: dict = Depends(current_customer),
):
    return subscriptions.list_subscriptions(customer_id=me["id"], page=page, page_size=page_size)


@router.get("/subscriptions/{subscription_id}")
def my_subscription(subscription_id: int, me: dict = Depends(current_customer)):
    sub = subscriptions.get_subscription(subscription_id, customer_id=me["id"])
    sub["transitions"] = []  # customers read only; no action buttons
    return sub


@router.get("/invoices")
def my_invoices(
    status: str | None = None,
    overdue: bool = False,
    q: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    me: dict = Depends(current_customer),
):
    return invoices.list_invoices(status, me["id"], overdue, q, None, None, page, page_size, hide_drafts=True)


@router.get("/invoices/{invoice_id}")
def my_invoice(invoice_id: int, me: dict = Depends(current_customer)):
    inv = invoices.get_invoice(invoice_id, customer_id=me["id"])
    inv["transitions"] = []
    return inv
