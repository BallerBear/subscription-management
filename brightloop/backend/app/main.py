from fastapi import FastAPI

from app.core.db import close_pool
from app.core.errors import register_error_handlers
from app.routers import (
    auth,
    catalog,
    clock,
    discounts,
    events,
    invoices,
    payments,
    portal,
    reports,
    subscriptions,
    users,
)

app = FastAPI(title="Brightloop API", version="0.1.0")
register_error_handlers(app)

for router_module in (
    auth,
    users,
    catalog,
    subscriptions,
    invoices,
    payments,
    discounts,
    reports,
    portal,
    clock,
    events,
):
    app.include_router(router_module.router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("shutdown")
def shutdown() -> None:
    close_pool()
