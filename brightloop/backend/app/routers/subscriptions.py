from fastapi import APIRouter, Depends, Query, status

from app.core.deps import require_role
from app.schemas.billing import DiscountAttachIn, SubscriptionIn, SubTransitionIn
from app.services import subscriptions as service

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
staff = require_role("ADMIN", "STAFF")


@router.get("")
def list_subscriptions(
    status: str | None = None,
    customer_id: int | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: dict = Depends(staff),
):
    return service.list_subscriptions(status, customer_id, q, page, page_size)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_subscription(body: SubscriptionIn, user: dict = Depends(staff)):
    data = body.model_dump()
    return service.create_subscription(
        user["id"], data["customer_id"], data["plan_id"], data["payment_term_id"],
        data["start_date"], data["expiry_date"], data["lines"],
    )


@router.get("/{subscription_id}")
def get_subscription(subscription_id: int, _: dict = Depends(staff)):
    return service.get_subscription(subscription_id)


@router.post("/{subscription_id}/transition")
def transition(subscription_id: int, body: SubTransitionIn, user: dict = Depends(staff)):
    return service.transition_subscription(user["id"], subscription_id, body.to_status)


@router.post("/{subscription_id}/discounts")
def attach_discount(subscription_id: int, body: DiscountAttachIn, user: dict = Depends(staff)):
    return service.add_discount(user["id"], subscription_id, body.discount_id)


@router.delete("/{subscription_id}/discounts/{discount_id}")
def detach_discount(subscription_id: int, discount_id: int, user: dict = Depends(staff)):
    return service.remove_discount(user["id"], subscription_id, discount_id)
