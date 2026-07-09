"""Thin assignment API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import (
    ServiceContainer,
    get_learner_id,
    get_services,
    require_ai_service,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.progress import ProgressSummaryResponse, ProgressUpdateRequest
from app.schemas.project import ProjectCreateRequest, ProjectResponse
from app.schemas.roadmap import RoadmapCreateRequest, RoadmapResponse

router = APIRouter()
Services = Annotated[ServiceContainer, Depends(get_services)]
LearnerId = Annotated[UUID, Depends(get_learner_id)]


@router.post(
    "/roadmap",
    response_model=RoadmapResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["roadmaps"],
    summary="Generate a personalized learning roadmap",
    description="Generates, validates, persists, embeds, and indexes a complete roadmap hierarchy.",
    responses={503: {"description": "AI or retrieval provider unavailable"}},
)
async def create_roadmap(
    command: RoadmapCreateRequest, request: Request, services: Services, learner_id: LearnerId
) -> RoadmapResponse:
    roadmaps = require_ai_service(services.roadmaps)
    return await roadmaps.create(learner_id, command, request.state.request_id)


@router.post(
    "/project",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
    summary="Generate a portfolio project",
    description="Accepts either a roadmap ID or a direct goal and skills list.",
    responses={404: {"description": "Roadmap not found"}},
)
async def create_project(
    command: ProjectCreateRequest, request: Request, services: Services, learner_id: LearnerId
) -> ProjectResponse:
    projects = require_ai_service(services.projects)
    return await projects.create(learner_id, command, request.state.request_id)


@router.post(
    "/chat",
    response_model=ChatResponse,
    tags=["chat"],
    summary="Ask a roadmap-grounded question",
    description=(
        "Runs filtered semantic retrieval and answers using only bounded retrieved context."
    ),
    responses={404: {"description": "Roadmap not found"}, 409: {"description": "Index not ready"}},
)
async def chat(
    command: ChatRequest, request: Request, services: Services, learner_id: LearnerId
) -> ChatResponse:
    chat_service = require_ai_service(services.chat)
    return await chat_service.chat(learner_id, command, request.state.request_id)


@router.patch(
    "/progress/{roadmap_id}",
    response_model=ProgressSummaryResponse,
    tags=["progress"],
    summary="Update learning progress",
)
async def update_progress(
    roadmap_id: UUID,
    command: ProgressUpdateRequest,
    services: Services,
    learner_id: LearnerId,
) -> ProgressSummaryResponse:
    return await services.progress.update(learner_id, roadmap_id, command)


@router.get(
    "/progress/{roadmap_id}",
    response_model=ProgressSummaryResponse,
    tags=["progress"],
    summary="Get roadmap progress statistics",
)
async def get_progress(
    roadmap_id: UUID, services: Services, learner_id: LearnerId
) -> ProgressSummaryResponse:
    return await services.progress.get_summary(learner_id, roadmap_id)
