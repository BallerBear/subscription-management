from fastapi import APIRouter, Depends, Query, status

from app.core.deps import require_role
from app.schemas.people import CustomerIn, CustomerPatch
from app.services import people

router = APIRouter(prefix="/customers", tags=["customers"])
staff = require_role("ADMIN", "STAFF")


@router.get("")
def list_customers(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: dict = Depends(staff),
):
    return people.list_customers(q, page, page_size)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerIn, user: dict = Depends(staff)):
    return people.create_customer(user["id"], body.model_dump())


@router.get("/{customer_id}")
def get_customer(customer_id: int, _: dict = Depends(staff)):
    return people.get_customer(customer_id)


@router.patch("/{customer_id}")
def update_customer(customer_id: int, body: CustomerPatch, user: dict = Depends(staff)):
    return people.update_customer(user["id"], customer_id, body.model_dump(exclude_unset=True))
