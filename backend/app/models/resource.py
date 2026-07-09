"""Learning resource persistence model."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Column, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship

from app.core.enums import Difficulty, ResourceStatus, ResourceType
from app.models.base import TimestampedModel, UUIDPrimaryKey, enum_column

if TYPE_CHECKING:
    from app.models.roadmap import Roadmap


class LearningResource(UUIDPrimaryKey, TimestampedModel, table=True):
    """Curated or AI-recommended resource linked to a roadmap entity."""

    __tablename__ = "learning_resources"
    __table_args__ = (
        UniqueConstraint("roadmap_id", "url_hash", name="uq_resource_roadmap_url"),
        CheckConstraint(
            "estimated_minutes IS NULL OR estimated_minutes > 0",
            name="ck_resource_minutes_positive",
        ),
        CheckConstraint(
            "relevance_score IS NULL OR "
            "(relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_resource_relevance_range",
        ),
        Index("ix_resource_roadmap_skill", "roadmap_id", "skill_id"),
        Index("ix_resource_roadmap_task", "roadmap_id", "task_id"),
    )

    learner_id: UUID = Field(index=True, nullable=False)
    roadmap_id: UUID = Field(foreign_key="roadmaps.id", ondelete="CASCADE", nullable=False)
    skill_id: UUID | None = Field(
        default=None, foreign_key="skills.id", ondelete="SET NULL", nullable=True
    )
    task_id: UUID | None = Field(
        default=None, foreign_key="tasks.id", ondelete="SET NULL", nullable=True
    )
    title: str = Field(max_length=240, nullable=False)
    url: str = Field(nullable=False)
    url_hash: str = Field(max_length=64, nullable=False)
    provider: str = Field(max_length=120, nullable=False)
    resource_type: ResourceType = Field(sa_column=enum_column(ResourceType))
    description: str = Field(nullable=False)
    difficulty: Difficulty = Field(sa_column=enum_column(Difficulty))
    estimated_minutes: int | None = Field(default=None, nullable=True)
    relevance_score: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(5, 4), nullable=True)
    )
    recommendation_reason: str = Field(nullable=False)
    status: ResourceStatus = Field(
        default=ResourceStatus.RECOMMENDED, sa_column=enum_column(ResourceStatus)
    )
    is_ai_recommended: bool = Field(default=True, nullable=False)

    roadmap: Roadmap = Relationship(
        sa_relationship=relationship("Roadmap", back_populates="resources")
    )
