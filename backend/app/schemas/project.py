"""Project API contracts."""

from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import Field, model_validator

from app.core.enums import Difficulty
from app.schemas.common import StrictSchema


class ProjectCreateRequest(StrictSchema):
    """Exclusive roadmap or direct goal-and-skills project input."""

    roadmap_id: UUID | None = None
    goal_title: Annotated[str | None, Field(min_length=3, max_length=200)] = None
    skills: Annotated[list[str] | None, Field(min_length=1, max_length=20)] = None
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    constraints: Annotated[list[str], Field(max_length=20)] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_mode(self) -> Self:
        roadmap_mode = self.roadmap_id is not None
        direct_mode = self.goal_title is not None and bool(self.skills)
        if roadmap_mode == direct_mode:
            raise ValueError("Provide either roadmap_id or goal_title with skills, but not both")
        if not roadmap_mode and (self.goal_title is None or not self.skills):
            raise ValueError("Direct mode requires goal_title and at least one skill")
        return self


class ProjectResponse(StrictSchema):
    project_id: UUID
    roadmap_id: UUID | None
    title: str
    description: str
    difficulty: Difficulty
    estimated_hours: Decimal
    skills: list[str]
    requirements: list[str]
    deliverables: list[str]
    acceptance_criteria: list[str]

