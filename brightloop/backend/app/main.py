from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.db import close_pool, connection
from app.core.errors import register_error_handlers
from app.routers import (
    auth,
    billing,
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
    billing,
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
    """A green response confirms the API can reach its database."""
    try:
        with connection() as conn:
            conn.execute("SELECT 1")
    except Exception:
        return JSONResponse({"status": "degraded", "db": "down"}, status_code=503)
    return {"status": "ok", "db": "up"}


@app.on_event("shutdown")
def shutdown() -> None:
    close_pool()
