"""Runtime settings policy tests."""

from typing import Any

import httpx
import pytest

from app.config.settings import (
    PRODUCTION_CORS_ALLOWED_ORIGIN_REGEX,
    Environment,
    Settings,
)
from app.main import create_app


def production_settings(**overrides: Any) -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.PRODUCTION,
        openrouter_api_key="test-openrouter-key",
        allow_anonymous_learner=False,
        **overrides,
    )


def test_production_trusts_render_loopbacks_and_frontend_origin_hosts() -> None:
    settings = production_settings(
        trusted_hosts=["adaptive-learning-ai-api.onrender.com"],
        cors_allowed_origins=[
            "https://adaptive-learning-ai.vercel.app",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    )

    assert settings.trusted_hosts == [
        "adaptive-learning-ai-api.onrender.com",
        "*.onrender.com",
        "localhost",
        "127.0.0.1",
        "adaptive-learning-ai.vercel.app",
    ]


def test_production_trusts_configured_and_default_cors_origins() -> None:
    settings = production_settings(
        cors_allowed_origins=["https://adaptive-learning-ai.vercel.app/"]
    )

    assert settings.cors_allowed_origins == [
        "https://adaptive-learning-ai.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    assert settings.cors_allowed_origin_regex == PRODUCTION_CORS_ALLOWED_ORIGIN_REGEX


def test_openrouter_environment_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/test-model")

    settings = Settings(_env_file=None)

    assert settings.openrouter_api_key is not None
    assert settings.openrouter_api_key.get_secret_value() == "test-openrouter-key"
    assert settings.llm_model == "openai/test-model"


def test_chroma_collection_name_sanitizes_embedding_model_only() -> None:
    settings = Settings(
        _env_file=None,
        embedding_model="OpenAI/Text Embedding:3 Small",
        embedding_dimensions=768,
    )

    assert settings.embedding_model == "OpenAI/Text Embedding:3 Small"
    assert (
        settings.chroma_collection_name
        == "learning_content--openai-text-embedding-3-small--d768--v1"
    )


async def test_generated_render_hostname_reaches_health_and_docs() -> None:
    app = create_app(
        production_settings(
            trusted_hosts=["adaptive-learning-ai-api.onrender.com"],
            cors_allowed_origins=["https://adaptive-learning-ai.vercel.app"],
        )
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://adaptive-learning-ai-16nq.onrender.com",
    ) as client:
        health = await client.get("/health")
        docs = await client.get("/docs")

    assert health.status_code == 200
    assert docs.status_code == 200


async def test_production_cors_allows_vercel_preview_preflight() -> None:
    origin = "https://adaptive-learning-ai-git-main-gagandeepsingh76.vercel.app"
    app = create_app(
        production_settings(cors_allowed_origins=["https://adaptive-learning-ai.vercel.app"])
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://adaptive-learning-ai-16nq.onrender.com",
    ) as client:
        response = await client.options(
            "/project",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,X-Learner-ID,X-Request-ID",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


async def test_production_cors_allows_localhost_preflight() -> None:
    app = create_app(
        production_settings(cors_allowed_origins=["https://adaptive-learning-ai.vercel.app"])
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://adaptive-learning-ai-16nq.onrender.com",
    ) as client:
        response = await client.options(
            "/project",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_production_cors_rejects_unconfigured_origin() -> None:
    app = create_app(
        production_settings(cors_allowed_origins=["https://adaptive-learning-ai.vercel.app"])
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://adaptive-learning-ai-16nq.onrender.com",
    ) as client:
        response = await client.options(
            "/project",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_global_wildcard_trusted_host_remains_forbidden_in_production() -> None:
    with pytest.raises(ValueError, match="wildcard CORS origins and trusted hosts"):
        production_settings(trusted_hosts=["*"])
