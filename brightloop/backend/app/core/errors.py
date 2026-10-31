from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, error: Exception
    ) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
