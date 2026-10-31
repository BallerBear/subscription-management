from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.db import connection
from app.core.deps import get_current_user, require_role
from app.services import audit

router = APIRouter(tags=["meta"])


@router.get("/meta/transitions")
def transitions(entity: Literal["SUBSCRIPTION", "INVOICE"], _: dict = Depends(get_current_user)):
    """The buttons the UI may show: straight from the status_transitions table."""
    with connection() as conn:
        return conn.execute(
            "SELECT from_status, to_status, action_label FROM status_transitions "
            "WHERE entity = %s AND action_label IS NOT NULL ORDER BY from_status, to_status",
            (entity,),
        ).fetchall()


@router.get("/audit")
def audit_log(
    table_name: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: dict = Depends(require_role("ADMIN")),
):
    return audit.list_audit(page, page_size, table_name)
