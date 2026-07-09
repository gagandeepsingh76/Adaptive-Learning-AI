"""Stable application exception hierarchy."""

from __future__ import annotations

from typing import Any


class ApplicationError(Exception):
    """Base error carrying only client-safe structured metadata."""

    code = "APPLICATION_ERROR"
    status_code = 500
    retryable = False

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class DomainValidationError(ApplicationError):
    """A request violates a business invariant."""

    code = "DOMAIN_VALIDATION_ERROR"
    status_code = 422


class ResourceNotFoundError(ApplicationError):
    """A requested aggregate does not exist in the learner scope."""

    code = "RESOURCE_NOT_FOUND"
    status_code = 404


class ResourceConflictError(ApplicationError):
    """The requested state transition conflicts with current state."""

    code = "RESOURCE_CONFLICT"
    status_code = 409


class ResourceForbiddenError(ApplicationError):
    """The caller cannot access the requested aggregate."""

    code = "RESOURCE_FORBIDDEN"
    status_code = 403


class InfrastructureError(ApplicationError):
    """An external infrastructure dependency failed."""

    code = "INFRASTRUCTURE_ERROR"
    status_code = 503
    retryable = True


class DatabaseError(InfrastructureError):
    """Database operation failed."""

    code = "DATABASE_UNAVAILABLE"


class VectorStoreError(InfrastructureError):
    """Vector storage or retrieval failed."""

    code = "RETRIEVAL_UNAVAILABLE"


class LLMProviderError(InfrastructureError):
    """LLM provider request failed."""

    code = "AI_PROVIDER_UNAVAILABLE"


class LLMProviderClientError(LLMProviderError):
    """LLM provider rejected a request with a client-actionable error."""

    code = "AI_PROVIDER_REQUEST_FAILED"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        status_code: int = 502,
        app_code: str | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.status_code = status_code
        if app_code is not None:
            self.code = app_code
        if retryable is not None:
            self.retryable = retryable


class LLMProviderConfigurationError(LLMProviderError):
    """LLM provider cannot be used until required configuration is supplied."""

    retryable = False


class LLMStructuredOutputError(ApplicationError):
    """The provider repeatedly returned invalid structured data."""

    code = "AI_OUTPUT_REJECTED"
    status_code = 502
    retryable = True


class AIResponseValidationError(LLMStructuredOutputError):
    """Decoded AI JSON violates schema or domain consistency rules."""

    code = "AI_RESPONSE_VALIDATION_FAILED"


class AIQualityError(ApplicationError):
    """Generated content failed the configured quality gate."""

    code = "AI_QUALITY_REJECTED"
    status_code = 502
    retryable = True


class PromptConfigurationError(ApplicationError):
    """A reviewed prompt asset is missing or inconsistent."""

    code = "PROMPT_CONFIGURATION_ERROR"
    status_code = 500


class PayloadTooLargeError(ApplicationError):
    """The incoming request body exceeds the configured limit."""

    code = "PAYLOAD_TOO_LARGE"
    status_code = 413
