"""Shared transport schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    """Base DTO that rejects undeclared input and coercion surprises."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ErrorBody(StrictSchema):
    """Client-safe error details."""

    code: str
    message: str
    request_id: str
    retryable: bool
    details: dict[str, Any] | None = None


class ErrorResponse(StrictSchema):
    """Stable API error envelope."""

    error: ErrorBody

