from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import require_role
from app.services import clock as clock_service

router = APIRouter(prefix="/clock", tags=["clock"])


class SetClockRequest(BaseModel):
    today: date


class AdvanceClockRequest(BaseModel):
    days: int = Field(default=0, ge=0)
    months: int = Field(default=0, ge=0)


@router.get("")
def get_clock():
    return clock_service.get_clock()


@router.put("")
def set_clock(
    payload: SetClockRequest,
    admin: dict = Depends(require_role("ADMIN")),
):
    return clock_service.set_clock(admin["id"], payload.today)


@router.post("/advance")
def advance_clock(
    payload: AdvanceClockRequest,
    admin: dict = Depends(require_role("ADMIN")),
):
    return clock_service.advance_clock(admin["id"], payload.days, payload.months)
