"""Learning progress persistence model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Column, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship

from app.core.enums import ProgressStatus, ProgressTargetType
from app.models.base import TimestampedModel, UUIDPrimaryKey, enum_column

if TYPE_CHECKING:
    from app.models.roadmap import Roadmap


class ProgressRecord(UUIDPrimaryKey, TimestampedModel, table=True):
    """Current progress for one learner and hierarchy target."""

    __tablename__ = "progress_records"
    __table_args__ = (
        UniqueConstraint(
            "learner_id", "roadmap_id", "scope_key", name="uq_progress_learner_scope"
        ),
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_progress_percent_range",
        ),
        CheckConstraint("time_spent_minutes >= 0", name="ck_progress_time_nonnegative"),
        Index("ix_progress_roadmap_target", "roadmap_id", "target_type"),
    )

    learner_id: UUID = Field(index=True, nullable=False)
    roadmap_id: UUID = Field(foreign_key="roadmaps.id", ondelete="CASCADE", nullable=False)
    skill_id: UUID | None = Field(
        default=None, foreign_key="skills.id", ondelete="CASCADE", nullable=True
    )
    task_id: UUID | None = Field(
        default=None, foreign_key="tasks.id", ondelete="CASCADE", nullable=True
    )
    subtask_id: UUID | None = Field(
        default=None, foreign_key="subtasks.id", ondelete="CASCADE", nullable=True
    )
    target_type: ProgressTargetType = Field(sa_column=enum_column(ProgressTargetType))
    scope_key: str = Field(max_length=80, nullable=False)
    status: ProgressStatus = Field(
        default=ProgressStatus.NOT_STARTED, sa_column=enum_column(ProgressStatus)
    )
    progress_percent: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(Numeric(5, 2), nullable=False)
    )
    time_spent_minutes: int = Field(default=0, nullable=False)
    notes: str | None = Field(default=None, nullable=True)
    started_at: datetime | None = Field(default=None, nullable=True)
    completed_at: datetime | None = Field(default=None, nullable=True)

    roadmap: Roadmap = Relationship(
        sa_relationship=relationship("Roadmap", back_populates="progress_records")
    )
