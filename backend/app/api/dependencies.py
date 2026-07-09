"""Thin FastAPI dependency adapters for business services."""

from dataclasses import dataclass
from typing import cast
from uuid import UUID

from fastapi import Header, Request

from app.exceptions import LLMProviderConfigurationError
from app.services.chat_service import ChatService
from app.services.progress_service import ProgressService
from app.services.project_service import ProjectService
from app.services.resource_service import LearningResourceService
from app.services.roadmap_service import RoadmapService


@dataclass(frozen=True, slots=True)
class ServiceContainer:
    roadmaps: RoadmapService | None
    projects: ProjectService | None
    chat: ChatService | None
    progress: ProgressService
    resources: LearningResourceService


def ai_provider_not_configured_error() -> LLMProviderConfigurationError:
    """Return a client-safe diagnostic for AI endpoints when Gemini is not configured."""
    return LLMProviderConfigurationError(
        "Gemini API Key (ALA_GEMINI_API_KEY) is missing.",
        details={
            "title": "AI Service Not Configured",
            "provider": "gemini",
            "missing_env": "ALA_GEMINI_API_KEY",
            "reason": "Gemini API Key (ALA_GEMINI_API_KEY) is missing.",
            "action": "Configure the backend environment, restart the backend, then retry.",
            "setup_steps": [
                "Add ALA_GEMINI_API_KEY to the backend environment.",
                "Restart the FastAPI backend so services are composed with Gemini.",
                "Run the health check again and retry the generation request.",
            ],
        },
    )


def require_ai_service[T](service: T | None) -> T:
    """Return an AI-backed service or raise the explicit configuration diagnostic."""
    if service is None:
        raise ai_provider_not_configured_error()
    return service


def get_services(request: Request) -> ServiceContainer:
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise ai_provider_not_configured_error()
    return cast(ServiceContainer, services)


def get_learner_id(
    request: Request, x_learner_id: UUID | None = Header(default=None)
) -> UUID:
    if x_learner_id is not None:
        return x_learner_id
    settings = request.app.state.settings
    if settings.allow_anonymous_learner:
        return cast(UUID, settings.anonymous_learner_id)
    raise LLMProviderConfigurationError("A trusted learner identity is required.")
