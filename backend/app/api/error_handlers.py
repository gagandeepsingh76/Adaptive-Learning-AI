"""Central exception-to-HTTP translation."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.logging import get_logger
from app.exceptions import ApplicationError

logger = get_logger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _error_response(
    *, code: str, message: str, request_id: str, retryable: bool, details: Any = None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id,
        "retryable": retryable,
    }
    if details is not None:
        body["details"] = details
    return {"error": body}


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized error mappings on an application."""

    @app.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        logger.warning(
            "application.error",
            error_code=exc.code,
            retryable=exc.retryable,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_response(
                code=exc.code,
                message=exc.message,
                request_id=_request_id(request),
                retryable=exc.retryable,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_response(
                code="REQUEST_VALIDATION_ERROR",
                message="The request payload is invalid.",
                request_id=_request_id(request),
                retryable=False,
                details={"errors": details},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_response(
                code="HTTP_ERROR",
                message=str(exc.detail),
                request_id=_request_id(request),
                retryable=False,
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "application.unexpected_error",
            error_type=type(exc).__name__,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content=_error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
                request_id=_request_id(request),
                retryable=False,
            ),
        )

