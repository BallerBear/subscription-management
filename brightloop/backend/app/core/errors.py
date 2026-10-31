import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(LookupError)
    async def not_found_handler(request: Request, error: LookupError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(ValueError)
    async def validation_handler(request: Request, error: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(psycopg.errors.UniqueViolation)
    async def duplicate_handler(request: Request, error: psycopg.Error) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": "A record with those details already exists."})

    @app.exception_handler(psycopg.errors.ForeignKeyViolation)
    async def foreign_key_handler(request: Request, error: psycopg.Error) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": "A referenced record does not exist."})

    @app.exception_handler(psycopg.errors.CheckViolation)
    async def check_handler(request: Request, error: psycopg.Error) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": error.diag.message_primary or "A value violates a database rule."})

    @app.exception_handler(psycopg.errors.RaiseException)
    async def business_rule_handler(request: Request, error: psycopg.Error) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": error.diag.message_primary or "The requested change is not allowed."})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, error: Exception
    ) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
