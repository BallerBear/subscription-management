from fastapi import APIRouter, Depends, Query, status

from app.core.deps import require_role
from app.schemas.catalog import (
    PlanCreate, PlanUpdate, ProductCreate, ProductUpdate, TaxCreate, TaxUpdate,
    VariantCreate, VariantUpdate,
)
from app.services import catalog as service

router = APIRouter(prefix="/catalog", tags=["catalog"])
admin_only = [Depends(require_role("ADMIN"))]


@router.get("/taxes", dependencies=admin_only)
def get_taxes(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    active_only: bool = False,
) -> dict:
    return service.list_taxes(page, page_size, active_only)


@router.post("/taxes", status_code=status.HTTP_201_CREATED)
def post_tax(payload: TaxCreate, user: dict = Depends(require_role("ADMIN"))) -> dict:
    return service.create_tax(user["id"], payload.model_dump())


@router.patch("/taxes/{tax_id}")
def patch_tax(tax_id: int, payload: TaxUpdate, user: dict = Depends(require_role("ADMIN"))) -> dict:
    return service.update_tax(user["id"], tax_id, payload.model_dump(exclude_unset=True))


@router.delete("/taxes/{tax_id}")
def delete_tax(tax_id: int, user: dict = Depends(require_role("ADMIN"))) -> dict:
    return service.deactivate_tax(user["id"], tax_id)


@router.get("/products", dependencies=admin_only)
def get_products(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    q: str | None = None, active_only: bool = False,
) -> dict:
    return service.list_products(page, page_size, q, active_only)


@router.get("/products/{product_id}", dependencies=admin_only)
def get_product(product_id: int) -> dict:
    return service.get_product(product_id)


@router.post("/products", status_code=status.HTTP_201_CREATED)
def post_product(payload: ProductCreate, user: dict = Depends(require_role("ADMIN"))) -> dict:
    return service.create_product(user["id"], payload.model_dump())


@router.patch("/products/{product_id}")
def patch_product(
    product_id: int, payload: ProductUpdate, user: dict = Depends(require_role("ADMIN"))
) -> dict:
    return service.update_product(user["id"], product_id, payload.model_dump(exclude_unset=True))


@router.delete("/products/{product_id}")
def delete_product(product_id: int, user: dict = Depends(require_role("ADMIN"))) -> dict:
    return service.deactivate_product(user["id"], product_id)


@router.get("/products/{product_id}/variants", dependencies=admin_only)
def get_variants(product_id: int) -> list[dict]:
    return service.list_variants(product_id)


@router.post(
    "/products/{product_id}/variants",
    status_code=status.HTTP_201_CREATED,
)
def post_variant(
    product_id: int, payload: VariantCreate, user: dict = Depends(require_role("ADMIN"))
) -> dict:
    return service.create_variant(user["id"], product_id, payload.model_dump())


@router.patch("/products/{product_id}/variants/{variant_id}")
def patch_variant(
    product_id: int, variant_id: int, payload: VariantUpdate,
    user: dict = Depends(require_role("ADMIN")),
) -> dict:
    return service.update_variant(
        user["id"], product_id, variant_id, payload.model_dump(exclude_unset=True)
    )


@router.delete("/products/{product_id}/variants/{variant_id}")
def delete_variant(
    product_id: int, variant_id: int, user: dict = Depends(require_role("ADMIN"))
) -> dict:
    return service.deactivate_variant(user["id"], product_id, variant_id)


@router.get("/plans", dependencies=admin_only)
def get_plans(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    active_only: bool = False,
) -> dict:
    return service.list_plans(page, page_size, active_only)


@router.post("/plans", status_code=status.HTTP_201_CREATED)
def post_plan(payload: PlanCreate, user: dict = Depends(require_role("ADMIN"))) -> dict:
    return service.create_plan(user["id"], payload.model_dump())


@router.patch("/plans/{plan_id}")
def patch_plan(plan_id: int, payload: PlanUpdate, user: dict = Depends(require_role("ADMIN"))) -> dict:
    return service.update_plan(user["id"], plan_id, payload.model_dump(exclude_unset=True))


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, user: dict = Depends(require_role("ADMIN"))) -> dict:
    return service.deactivate_plan(user["id"], plan_id)
