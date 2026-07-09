"""Roadmap API contracts."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.core.enums import ExperienceLevel, LearningStyle
from app.schemas.common import StrictSchema


class RoadmapCreateRequest(StrictSchema):
    """Personalized roadmap generation input."""

    goal_title: Annotated[str, Field(min_length=3, max_length=200, examples=["AI Engineer"])]
    goal_description: Annotated[str | None, Field(max_length=2000)] = None
    experience_level: ExperienceLevel = ExperienceLevel.BEGINNER
    learning_style: LearningStyle = LearningStyle.MIXED
    weekly_hours: Annotated[Decimal, Field(gt=0, le=168)] = Decimal("10")
    existing_skills: Annotated[list[str], Field(max_length=30)] = Field(default_factory=list)
    constraints: Annotated[list[str], Field(max_length=20)] = Field(default_factory=list)


class SubtaskResponse(StrictSchema):
    id: UUID
    title: str
    description: str
    completion_criteria: str
    estimated_hours: Decimal
    order_index: int


class TaskResponse(StrictSchema):
    id: UUID
    title: str
    description: str
    difficulty: str
    estimated_hours: Decimal
    order_index: int
    learning_outcomes: list[str]
    subtasks: list[SubtaskResponse]


class SkillResponse(StrictSchema):
    id: UUID
    title: str
    description: str
    target_proficiency: str
    estimated_hours: Decimal
    order_index: int
    tasks: list[TaskResponse]


class RoadmapResponse(StrictSchema):
    roadmap_id: UUID
    goal_title: str
    estimated_hours: Decimal
    skills: list[SkillResponse]

