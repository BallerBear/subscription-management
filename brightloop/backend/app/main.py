from fastapi import FastAPI

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
