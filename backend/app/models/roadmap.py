"""Roadmap hierarchy persistence models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, Column, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship

from app.core.enums import Difficulty, ExperienceLevel, IndexStatus, LearningStyle, RoadmapStatus
from app.models.base import TimestampedModel, UUIDPrimaryKey, enum_column

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.progress import ProgressRecord
    from app.models.project import Project
    from app.models.resource import LearningResource


class Roadmap(UUIDPrimaryKey, TimestampedModel, table=True):
    """Root learning plan aggregate and vector projection state."""

    __tablename__ = "roadmaps"
    __table_args__ = (
        CheckConstraint("weekly_hours > 0", name="ck_roadmap_weekly_hours_positive"),
        CheckConstraint("estimated_hours > 0", name="ck_roadmap_hours_positive"),
        CheckConstraint("content_version >= 1", name="ck_roadmap_content_version"),
        CheckConstraint(
            "indexed_content_version IS NULL OR indexed_content_version <= content_version",
            name="ck_roadmap_indexed_version",
        ),
        Index("ix_roadmap_learner_created", "learner_id", "created_at"),
        Index("ix_roadmap_learner_fingerprint", "learner_id", "request_fingerprint"),
        Index("ix_roadmap_index_recovery", "index_status", "updated_at"),
    )

    learner_id: UUID = Field(index=True, nullable=False)
    goal_title: str = Field(max_length=200, nullable=False)
    goal_description: str | None = Field(default=None, nullable=True)
    experience_level: ExperienceLevel = Field(sa_column=enum_column(ExperienceLevel))
    learning_style: LearningStyle = Field(sa_column=enum_column(LearningStyle))
    weekly_hours: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    estimated_hours: Decimal = Field(sa_column=Column(Numeric(8, 2), nullable=False))
    status: RoadmapStatus = Field(
        default=RoadmapStatus.ACTIVE, sa_column=enum_column(RoadmapStatus)
    )
    content_version: int = Field(default=1, nullable=False)
    indexed_content_version: int | None = Field(default=None, nullable=True)
    index_status: IndexStatus = Field(
        default=IndexStatus.PENDING, sa_column=enum_column(IndexStatus)
    )
    indexed_at: datetime | None = Field(default=None, nullable=True)
    request_fingerprint: str = Field(max_length=64, nullable=False)
    generation_prompt_version_id: UUID = Field(
        foreign_key="prompt_versions.id", ondelete="RESTRICT", nullable=False
    )

    skills: list[Skill] = Relationship(
        sa_relationship=relationship(
            "Skill", back_populates="roadmap", cascade="all, delete-orphan"
        )
    )
    projects: list[Project] = Relationship(
        sa_relationship=relationship("Project", back_populates="roadmap")
    )
    conversations: list[Conversation] = Relationship(
        sa_relationship=relationship("Conversation", back_populates="roadmap")
    )
    progress_records: list[ProgressRecord] = Relationship(
        sa_relationship=relationship("ProgressRecord", back_populates="roadmap")
    )
    resources: list[LearningResource] = Relationship(
        sa_relationship=relationship("LearningResource", back_populates="roadmap")
    )


class Skill(UUIDPrimaryKey, TimestampedModel, table=True):
    """Ordered skill stage within a roadmap."""

    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("roadmap_id", "order_index", name="uq_skill_roadmap_order"),
        CheckConstraint("estimated_hours > 0", name="ck_skill_hours_positive"),
        CheckConstraint("order_index >= 0", name="ck_skill_order_nonnegative"),
        Index("ix_skill_roadmap_title", "roadmap_id", "title"),
    )

    roadmap_id: UUID = Field(foreign_key="roadmaps.id", ondelete="CASCADE", nullable=False)
    title: str = Field(max_length=160, nullable=False)
    description: str = Field(nullable=False)
    target_proficiency: str = Field(max_length=32, nullable=False)
    estimated_hours: Decimal = Field(sa_column=Column(Numeric(7, 2), nullable=False))
    order_index: int = Field(nullable=False)

    roadmap: Roadmap = Relationship(
        sa_relationship=relationship("Roadmap", back_populates="skills")
    )
    tasks: list[Task] = Relationship(
        sa_relationship=relationship(
            "Task", back_populates="skill", cascade="all, delete-orphan"
        )
    )


class Task(UUIDPrimaryKey, TimestampedModel, table=True):
    """Ordered measurable work item within a skill."""

    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("skill_id", "order_index", name="uq_task_skill_order"),
        CheckConstraint("estimated_hours > 0", name="ck_task_hours_positive"),
        CheckConstraint("order_index >= 0", name="ck_task_order_nonnegative"),
        Index("ix_task_skill_title", "skill_id", "title"),
    )

    skill_id: UUID = Field(foreign_key="skills.id", ondelete="CASCADE", nullable=False)
    title: str = Field(max_length=200, nullable=False)
    description: str = Field(nullable=False)
    difficulty: Difficulty = Field(sa_column=enum_column(Difficulty))
    estimated_hours: Decimal = Field(sa_column=Column(Numeric(7, 2), nullable=False))
    order_index: int = Field(nullable=False)
    learning_outcomes: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )

    skill: Skill = Relationship(sa_relationship=relationship("Skill", back_populates="tasks"))
    subtasks: list[Subtask] = Relationship(
        sa_relationship=relationship(
            "Subtask", back_populates="task", cascade="all, delete-orphan"
        )
    )


class Subtask(UUIDPrimaryKey, TimestampedModel, table=True):
    """Smallest trackable action in a learning roadmap."""

    __tablename__ = "subtasks"
    __table_args__ = (
        UniqueConstraint("task_id", "order_index", name="uq_subtask_task_order"),
        CheckConstraint("estimated_hours > 0", name="ck_subtask_hours_positive"),
        CheckConstraint("order_index >= 0", name="ck_subtask_order_nonnegative"),
        Index("ix_subtask_task_title", "task_id", "title"),
    )

    task_id: UUID = Field(foreign_key="tasks.id", ondelete="CASCADE", nullable=False)
    title: str = Field(max_length=220, nullable=False)
    description: str = Field(nullable=False)
    completion_criteria: str = Field(nullable=False)
    estimated_hours: Decimal = Field(sa_column=Column(Numeric(6, 2), nullable=False))
    order_index: int = Field(nullable=False)

    task: Task = Relationship(sa_relationship=relationship("Task", back_populates="subtasks"))
