"""Operational health endpoints."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["operations"])


class AIProviderStatus(BaseModel):
    """Client-safe provider readiness metadata for diagnostics screens."""

    provider: str
    configured: bool
    status: str
    llm_model: str
    embedding_model: str
    embedding_dimensions: int
    reason: str | None = None
    action: str | None = None
    missing_env: str | None = None


class HealthResponse(BaseModel):
    """Health status returned to deployment probes."""

    status: str
    version: str
    environment: str
    ai_provider: AIProviderStatus


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Return process health and immutable deployment metadata."""
    settings = request.app.state.settings
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment.value,
        ai_provider=_ai_provider_status(request),
    )


@router.get("/health/live", response_model=HealthResponse)
async def liveness(request: Request) -> HealthResponse:
    """Report process liveness without calling external dependencies."""
    return await health(request)


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(request: Request) -> HealthResponse:
    """Verify database connectivity and required runtime composition."""
    await request.app.state.database.ping()
    settings = request.app.state.settings
    ai_provider = _ai_provider_status(request)
    status_value = "ready" if ai_provider.status == "ready" else "degraded"
    return HealthResponse(
        status=status_value,
        version=settings.app_version,
        environment=settings.environment.value,
        ai_provider=ai_provider,
    )


def _ai_provider_status(request: Request) -> AIProviderStatus:
    settings = request.app.state.settings
    services = getattr(request.app.state, "services", None)
    provider_ready = bool(
        getattr(services, "roadmaps", None)
        and getattr(services, "projects", None)
        and getattr(services, "chat", None)
    )

    if settings.gemini_api_key is None:
        return AIProviderStatus(
            provider="gemini",
            configured=False,
            status="unconfigured",
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            embedding_dimensions=settings.embedding_dimensions,
            reason="Gemini API Key (ALA_GEMINI_API_KEY) is missing.",
            action="Configure the backend environment, restart the backend, then retry.",
            missing_env="ALA_GEMINI_API_KEY",
        )

    return AIProviderStatus(
        provider="gemini",
        configured=True,
        status="ready" if provider_ready else "unavailable",
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        embedding_dimensions=settings.embedding_dimensions,
        reason=(
            None
            if provider_ready
            else "Gemini credentials are present, but AI services did not initialize."
        ),
        action=None if provider_ready else "Check backend startup logs and restart the service.",
        missing_env=None,
    )
