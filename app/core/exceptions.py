"""
Global exception handlers.

Registered in main.py via app.add_exception_handler().
Ensures every error — expected or unexpected — returns structured JSON
instead of raw Python tracebacks or FastAPI's default plain-text responses.
"""

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers all global exception handlers onto the FastAPI app instance.
    Called once in main.py during app creation.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        Handles all intentional HTTP errors (404, 400, 409, etc.).
        Wraps FastAPI's default response in our standard error envelope.
        """
        logger.warning(
            "HTTP error",
            extra={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": str(request.url),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Handles Pydantic validation failures on incoming request data.
        FastAPI raises this when request body/query params don't match the schema.

        Default FastAPI returns a hard-to-read nested structure.
        We flatten it into a readable list of field errors.
        """
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " → ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })

        logger.warning(
            "Request validation failed",
            extra={"path": str(request.url), "errors": errors},
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "status_code": 422,
                "detail": "Request validation failed",
                "errors": errors,
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """
        Catches any exception not handled by the above handlers.
        Logs the full traceback internally but returns a safe generic message
        to the client — never leak stack traces in production.
        """
        logger.error(
            "Unhandled exception",
            extra={"path": str(request.url), "error": str(exc)},
            exc_info=True,  # includes full traceback in the log
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "status_code": 500,
                "detail": "An internal server error occurred.",
                "path": str(request.url.path),
            },
        )