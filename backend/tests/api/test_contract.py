"""HTTP and OpenAPI contract tests."""

from decimal import Decimal
from uuid import UUID, uuid4

import httpx

from app.api.dependencies import ServiceContainer, get_services
from app.config.settings import Environment, Settings
from app.main import create_app
from app.schemas.roadmap import (
    RoadmapCreateRequest,
    RoadmapResponse,
    SkillResponse,
    SubtaskResponse,
    TaskResponse,
)


def test_openapi_contains_all_assignment_routes() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment=Environment.TEST,
            database_url="sqlite+aiosqlite:///:memory:",
            trusted_hosts=["testserver"],
        )
    )
    schema = app.openapi()

    assert "post" in schema["paths"]["/roadmap"]
    assert "post" in schema["paths"]["/project"]
    assert "post" in schema["paths"]["/chat"]
    assert "patch" in schema["paths"]["/progress/{roadmap_id}"]
    assert "get" in schema["paths"]["/health/ready"]


async def test_health_and_unconfigured_provider_error_are_safe() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment=Environment.TEST,
            database_url="sqlite+aiosqlite:///:memory:",
            trusted_hosts=["testserver"],
        )
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        health = await client.get("/health")
        readiness = await client.get("/health/ready")
        unavailable = await client.post(
            "/roadmap",
            json={
                "goal_title": "Backend Engineer",
                "goal_description": "Build production APIs.",
                "experience_level": "intermediate",
                "learning_style": "hands_on",
                "weekly_hours": 8,
                "existing_skills": ["Python"],
                "constraints": ["portfolio-ready"],
            },
        )
        project_unavailable = await client.post(
            "/project",
            json={
                "goal_title": "AI Engineer",
                "skills": ["Python", "RAG"],
                "difficulty": "intermediate",
                "constraints": ["portfolio-ready"],
            },
        )
        chat_unavailable = await client.post(
            "/chat",
            json={
                "roadmap_id": "00000000-0000-4000-8000-000000000999",
                "question": "What should I learn first?",
            },
        )
        progress = await client.get("/progress/00000000-0000-4000-8000-000000000999")

    assert health.status_code == 200
    assert health.json()["ai_provider"]["status"] == "unconfigured"
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "degraded"
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "AI_PROVIDER_UNAVAILABLE"
    assert unavailable.json()["error"]["retryable"] is False
    assert unavailable.json()["error"]["details"]["missing_env"] == "OPENROUTER_API_KEY"
    assert project_unavailable.status_code == 503
    assert project_unavailable.json()["error"]["details"]["missing_env"] == "OPENROUTER_API_KEY"
    assert chat_unavailable.status_code == 503
    assert chat_unavailable.json()["error"]["details"]["missing_env"] == "OPENROUTER_API_KEY"
    assert progress.status_code == 404
    assert progress.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "traceback" not in unavailable.text.casefold()


async def test_roadmap_endpoint_returns_generated_response() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment=Environment.TEST,
            database_url="sqlite+aiosqlite:///:memory:",
            trusted_hosts=["testserver"],
        )
    )
    app.dependency_overrides[get_services] = lambda: ServiceContainer(
        roadmaps=_SuccessfulRoadmapService(),  # type: ignore[arg-type]
        projects=None,
        chat=None,
        progress=None,  # type: ignore[arg-type]
        resources=None,  # type: ignore[arg-type]
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        response = await client.post(
            "/roadmap",
            json={
                "goal_title": "Backend Engineer",
                "goal_description": "Build production APIs.",
                "experience_level": "intermediate",
                "learning_style": "hands_on",
                "weekly_hours": 8,
                "existing_skills": ["Python"],
                "constraints": ["portfolio-ready"],
            },
        )

    body = response.json()
    assert response.status_code == 201
    assert body["goal_title"] == "Backend Engineer"
    assert body["skills"][0]["tasks"][0]["difficulty"] == "beginner"
    assert body["skills"][0]["tasks"][0]["subtasks"][0]["completion_criteria"]


async def test_project_request_enforces_exclusive_modes() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment=Environment.TEST,
            database_url="sqlite+aiosqlite:///:memory:",
            trusted_hosts=["testserver"],
        )
    )
    app.dependency_overrides[get_services] = lambda: object()
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        response = await client.post("/project", json={"goal_title": "AI Engineer"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


class _SuccessfulRoadmapService:
    async def create(
        self, learner_id: UUID, command: RoadmapCreateRequest, request_id: str | None = None
    ) -> RoadmapResponse:
        del learner_id, request_id
        return RoadmapResponse(
            roadmap_id=uuid4(),
            goal_title=command.goal_title,
            estimated_hours=Decimal("10.0"),
            skills=[
                SkillResponse(
                    id=uuid4(),
                    title="Python APIs",
                    description="Build robust typed web APIs with validation and tests.",
                    target_proficiency="intermediate",
                    estimated_hours=Decimal("10.0"),
                    order_index=0,
                    tasks=[
                        TaskResponse(
                            id=uuid4(),
                            title="FastAPI service",
                            description="Implement a layered HTTP service with strict contracts.",
                            difficulty="beginner",
                            estimated_hours=Decimal("10.0"),
                            order_index=0,
                            learning_outcomes=["Design typed API boundaries"],
                            subtasks=[
                                SubtaskResponse(
                                    id=uuid4(),
                                    title="Create routes",
                                    description="Create and test typed route handlers.",
                                    completion_criteria="Contract tests pass.",
                                    estimated_hours=Decimal("10.0"),
                                    order_index=0,
                                )
                            ],
                        )
                    ],
                )
            ],
        )
