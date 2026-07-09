"""Request correlation and duration middleware."""

from __future__ import annotations

import re
from time import perf_counter
from uuid import uuid4

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config.logging import get_logger

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class RequestContextMiddleware:
    """Bind request IDs to logs and return them on every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = get_logger(__name__)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        supplied = headers.get("x-request-id", "")
        request_id = supplied if _REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append("x-request-id", request_id)
            await send(message)

        self.logger.info(
            "http.request.started", method=scope["method"], path=scope["path"]
        )
        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            self.logger.info(
                "http.request.completed",
                method=scope["method"],
                path=scope["path"],
                status_code=status_code,
                duration_ms=round((perf_counter() - start) * 1000, 3),
            )
            structlog.contextvars.clear_contextvars()

