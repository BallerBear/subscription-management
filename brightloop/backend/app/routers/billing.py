from fastapi import APIRouter, Depends

from app.core.deps import require_staff
from app.services import billing as billing_service

router = APIRouter(tags=["billing"])


@router.post("/billing/run")
def run_billing(auto_confirm: bool = True, user: dict = Depends(require_staff)):
    """Bill every subscription that is due as of app_clock.today.

    No date is accepted on purpose: the Time Machine controls 'today'.
    Optional query param: /billing/run?auto_confirm=false
    """
    return billing_service.run_billing(user["id"], auto_confirm)


@router.post("/invoices/confirm-drafts")
def confirm_drafts(user: dict = Depends(require_staff)):
    """Confirm every DRAFT invoice in one go."""
    return billing_service.confirm_all_drafts(user["id"])
