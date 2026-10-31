"""Staff list and (de)activation. Creating staff is POST /auth/staff (admin only)."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.deps import require_role
from app.core.errors import friendly_error
from app.services import people

router = APIRouter(prefix="/users", tags=["users"])


class ActiveIn(BaseModel):
    is_active: bool


@router.get("")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: dict = Depends(require_role("ADMIN")),
):
    return people.list_users(page, page_size)


@router.patch("/{user_id}")
def set_active(user_id: int, body: ActiveIn, admin: dict = Depends(require_role("ADMIN"))):
    if user_id == admin["id"]:
        raise friendly_error("You can't deactivate your own account", 400)
    return people.set_user_active(admin["id"], user_id, body.is_active)
