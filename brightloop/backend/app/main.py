from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.db import close_pool, connection
from app.core.errors import register_error_handlers
from app.routers import (
    auth,
    billing,
    catalog,
    clock,
    customers,
    discounts,
    events,
    invoices,
    lookups,
    meta,
    payments,
    portal,
    reports,
    subscriptions,
    users,
)
from app.services.common import RuleError

app = FastAPI(title="Brightloop API", version="0.1.0")
register_error_handlers(app)


@app.exception_handler(RuleError)
async def _rule_error(request, exc: RuleError):
    # Services raise RuleError (no FastAPI import); this turns it into the standard error body.
    return JSONResponse(
        {"message": exc.message, "fields": {exc.field: exc.message} if exc.field else {}},
        status_code=exc.status,
    )


for router_module in (
    auth,
    users,
    customers,
    lookups,
    meta,
    billing,
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
