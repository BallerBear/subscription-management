from fastapi import APIRouter, Depends

from app.core.deps import require_role
from app.services import lookups

router = APIRouter(prefix="/lookups", tags=["lookups"])


@router.get("")
def get_lookups(_: dict = Depends(require_role("ADMIN", "STAFF"))):
    """Active plans, products (+variants), payment terms and discounts for forms."""
    return lookups.get_lookups()
