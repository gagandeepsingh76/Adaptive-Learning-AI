"""Domain and infrastructure exception types."""

from app.exceptions.base import (
    AIQualityError,
    AIResponseValidationError,
    ApplicationError,
    DatabaseError,
    DomainValidationError,
    InfrastructureError,
    LLMProviderConfigurationError,
    LLMProviderError,
    LLMStructuredOutputError,
    PayloadTooLargeError,
    PromptConfigurationError,
    ResourceConflictError,
    ResourceForbiddenError,
    ResourceNotFoundError,
    VectorStoreError,
)

__all__ = [
    "AIQualityError",
    "AIResponseValidationError",
    "ApplicationError",
    "DatabaseError",
    "DomainValidationError",
    "InfrastructureError",
    "LLMProviderConfigurationError",
    "LLMProviderError",
    "LLMStructuredOutputError",
    "PayloadTooLargeError",
    "PromptConfigurationError",
    "ResourceConflictError",
    "ResourceForbiddenError",
    "ResourceNotFoundError",
    "VectorStoreError",
]
