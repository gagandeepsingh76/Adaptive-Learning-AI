"""Runtime settings policy tests."""

from typing import Any

import httpx
import pytest

from app.config.settings import Environment, Settings
from app.main import create_app


def production_settings(**overrides: Any) -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.PRODUCTION,
        gemini_api_key="test-gemini-key",
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


def test_global_wildcard_trusted_host_remains_forbidden_in_production() -> None:
    with pytest.raises(ValueError, match="wildcard CORS origins and trusted hosts"):
        production_settings(trusted_hosts=["*"])
