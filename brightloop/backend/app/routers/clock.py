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


@router.put("", dependencies=[Depends(require_role("ADMIN"))])
def set_clock(payload: SetClockRequest):
    # Authentication integration must provide the real user_id.
    # This temporary placeholder is intentionally not fabricated.
    raise NotImplementedError("Pass the authenticated admin user_id once auth is wired")


@router.post("/advance", dependencies=[Depends(require_role("ADMIN"))])
def advance_clock(payload: AdvanceClockRequest):
    raise NotImplementedError("Pass the authenticated admin user_id once auth is wired")