from fastapi import APIRouter, Depends

from app.core.deps import require_role
from app.schemas.billing import BillingRunIn
from app.services import billing as service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/run")
def run(body: BillingRunIn | None = None, user: dict = Depends(require_role("ADMIN", "STAFF"))):
    """Bill everything due as of app_clock.today. Safe to click twice: the second run creates nothing."""
    return service.run_billing(user["id"], auto_confirm=(body.auto_confirm if body else True))
