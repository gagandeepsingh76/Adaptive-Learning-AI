"""Streaming-safe request body size enforcement."""

from __future__ import annotations

import json
from typing import Any

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class PayloadLimitMiddleware:
    """Reject request bodies that exceed the configured byte limit."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self.max_bytes:
            await self._send_rejection(scope, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _BodyLimitExceeded
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _BodyLimitExceeded:
            await self._send_rejection(scope, send)

    async def _send_rejection(self, scope: Scope, send: Send) -> None:
        request_id = scope.get("state", {}).get("request_id", "unknown")
        body: dict[str, Any] = {
            "error": {
                "code": "PAYLOAD_TOO_LARGE",
                "message": "Request body exceeds the configured size limit.",
                "request_id": request_id,
                "retryable": False,
            }
        }
        encoded = json.dumps(body).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(encoded)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": encoded})


class _BodyLimitExceeded(Exception):
    """Internal control-flow signal for streamed oversized bodies."""

