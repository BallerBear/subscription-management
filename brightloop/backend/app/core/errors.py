"""Friendly errors. Every error the API returns has the same shape:

    {"message": "Human sentence", "fields": {"email": "Human sentence"}}

`fields` is empty when the problem is not tied to one input.

Usage in any router:
    raise friendly_error("Plan is closed", 409)
    raise friendly_error("Email already used", 409, field="email")
"""

import psycopg.errors as pgerr
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# DB constraint name -> (field or None, sentence). Teammates: add yours here.
CONSTRAINT_MESSAGES: dict[str, tuple[str | None, str]] = {
    "users_email_unique": ("email", "An account with this email already exists"),
    "products_name_unique": ("name", "A product with this name already exists"),
    "plans_name_unique": ("name", "A plan with this name already exists"),
    "one_invoice_per_period": (None, "This period has already been billed"),
    "discount_within_limit": (None, "This discount has reached its usage limit"),
    "invoice_paid_in_range": (None, "Payment is more than the invoice total"),
    "sub_dates_ordered": ("expiry_date", "Expiry date must be after the start date"),
    "plan_dates_ordered": ("available_to", "End date must be on or after the start date"),
}


def friendly_error(message: str, status: int = 400, field: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"message": message, "fields": {field: message} if field else {}},
    )


def _body(message: str, fields: dict[str, str] | None = None) -> dict:
    return {"message": message, "fields": fields or {}}


def _clean(err: dict) -> str:
    """Turn a pydantic error into a sentence a customer can act on."""
    kind = err.get("type", "")
    ctx = err.get("ctx") or {}
    if kind == "missing":
        return "This field is required"
    if kind == "string_too_short":
        return f"Use at least {ctx.get('min_length')} characters"
    if kind == "string_too_long":
        return f"Use at most {ctx.get('max_length')} characters"
    if kind == "value_error":
        return str(err.get("msg", "Invalid value")).replace("Value error, ", "")
    if kind.startswith(("int", "float")):
        return "Enter a valid number"
    if kind == "greater_than_equal":
        return f"Must be {ctx.get('ge')} or more"
    return "Invalid value"


async def _validation_handler(request: Request, exc: RequestValidationError):
    fields: dict[str, str] = {}
    for e in exc.errors():
        path = [str(p) for p in e["loc"] if p not in ("body", "query", "path")]
        fields.setdefault(".".join(path) or "_", _clean(e))
    return JSONResponse(422, _body("Please fix the highlighted fields", fields))


async def _http_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "message" in detail:
        content = {"message": detail["message"], "fields": detail.get("fields", {})}
    else:
        content = _body(str(detail))
    return JSONResponse(exc.status_code, content)


def _constraint_response(exc: pgerr.Error, status: int, fallback: str):
    name = exc.diag.constraint_name or ""
    field, message = CONSTRAINT_MESSAGES.get(name, (None, fallback))
    return JSONResponse(status, _body(message, {field: message} if field else {}))


async def _db_rule_handler(request: Request, exc: pgerr.RaiseException):
    # Messages raised by our triggers are already written for humans.
    return JSONResponse(409, _body(exc.diag.message_primary or "That action isn't allowed right now"))


async def _unique_handler(request: Request, exc: pgerr.UniqueViolation):
    return _constraint_response(exc, 409, "That already exists")


async def _fk_handler(request: Request, exc: pgerr.ForeignKeyViolation):
    return _constraint_response(exc, 409, "That item is linked to something that doesn't exist or is still in use")


async def _check_handler(request: Request, exc: pgerr.CheckViolation):
    return _constraint_response(exc, 422, "One of the values isn't allowed")


async def _unhandled(request: Request, exc: Exception):
    return JSONResponse(500, _body("Something went wrong on our side. Please try again."))


def register_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_handler)
    app.add_exception_handler(pgerr.RaiseException, _db_rule_handler)
    app.add_exception_handler(pgerr.UniqueViolation, _unique_handler)
    app.add_exception_handler(pgerr.ForeignKeyViolation, _fk_handler)
    app.add_exception_handler(pgerr.CheckViolation, _check_handler)
    app.add_exception_handler(Exception, _unhandled)
