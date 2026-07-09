"""Strict schemas accepted from the AI platform."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.core.enums import Difficulty


class AIOutput(BaseModel):
    """Strict base for every model-generated object."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class GeneratedSubtask(AIOutput):
    title: Annotated[str, Field(min_length=3, max_length=220)]
    description: Annotated[str, Field(min_length=10, max_length=2000)]
    completion_criteria: Annotated[str, Field(min_length=5, max_length=1000)]
    estimated_hours: Annotated[float, Field(gt=0, le=100)]
    order_index: Annotated[int, Field(ge=0)]


class GeneratedTask(AIOutput):
    title: Annotated[str, Field(min_length=3, max_length=200)]
    description: Annotated[str, Field(min_length=10, max_length=3000)]
    difficulty: Difficulty
    estimated_hours: Annotated[float, Field(gt=0, le=500)]
    order_index: Annotated[int, Field(ge=0)]
    learning_outcomes: Annotated[list[str], Field(min_length=1, max_length=10)]
    subtasks: Annotated[list[GeneratedSubtask], Field(min_length=1, max_length=20)]


class GeneratedSkill(AIOutput):
    title: Annotated[str, Field(min_length=2, max_length=160)]
    description: Annotated[str, Field(min_length=10, max_length=3000)]
    target_proficiency: Annotated[str, Field(min_length=3, max_length=32)]
    estimated_hours: Annotated[float, Field(gt=0, le=2000)]
    order_index: Annotated[int, Field(ge=0)]
    tasks: Annotated[list[GeneratedTask], Field(min_length=1, max_length=30)]


class GeneratedRoadmap(AIOutput):
    goal_title: Annotated[str, Field(min_length=3, max_length=200)]
    summary: Annotated[str, Field(min_length=20, max_length=4000)]
    estimated_hours: Annotated[float, Field(gt=0, le=10000)]
    skills: Annotated[list[GeneratedSkill], Field(min_length=1, max_length=30)]


class GeneratedProject(AIOutput):
    title: Annotated[str, Field(min_length=3, max_length=220)]
    description: Annotated[str, Field(min_length=20, max_length=5000)]
    difficulty: Difficulty
    estimated_hours: Annotated[float, Field(gt=0, le=1000)]
    skills: Annotated[list[str], Field(min_length=1, max_length=20)]
    requirements: Annotated[list[str], Field(min_length=1, max_length=30)]
    deliverables: Annotated[list[str], Field(min_length=1, max_length=30)]
    acceptance_criteria: Annotated[list[str], Field(min_length=1, max_length=30)]


class ChatAnswer(AIOutput):
    answer: Annotated[str, Field(min_length=1, max_length=12000)]
    source_ids: Annotated[list[str], Field(max_length=20)]
    confidence: Literal["low", "medium", "high"]
    limitations: Annotated[list[str], Field(max_length=10)] = Field(default_factory=list)


class FollowUpQuestions(AIOutput):
    questions: Annotated[list[str], Field(min_length=2, max_length=3)]


class QueryExpansion(AIOutput):
    canonical_query: Annotated[str, Field(min_length=2, max_length=1000)]
    alternatives: Annotated[list[str], Field(max_length=3)]
    mentioned_entity: str | None = None


class GeneratedResource(AIOutput):
    title: Annotated[str, Field(min_length=2, max_length=240)]
    url: HttpUrl
    provider: Annotated[str, Field(min_length=2, max_length=120)]
    description: Annotated[str, Field(min_length=10, max_length=2000)]
    recommendation_reason: Annotated[str, Field(min_length=10, max_length=1000)]


class EvaluationOutput(AIOutput):
    overall_score: Annotated[float, Field(ge=0, le=1)]
    dimension_scores: dict[str, Annotated[float, Field(ge=0, le=1)]]
    reasons: list[str]
    recommendations: list[str]
    passed: bool
