"""Generated project persistence models."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, Column, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship

from app.core.enums import Difficulty, ProjectStatus
from app.models.base import TimestampedModel, UUIDPrimaryKey, enum_column

if TYPE_CHECKING:
    from app.models.roadmap import Roadmap


class Project(UUIDPrimaryKey, TimestampedModel, table=True):
    """Portfolio project generated from a roadmap or direct goal and skills."""

    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("estimated_hours > 0", name="ck_project_hours_positive"),
        Index("ix_project_learner_created", "learner_id", "created_at"),
        Index("ix_project_roadmap_created", "roadmap_id", "created_at"),
        Index("ix_project_learner_fingerprint", "learner_id", "request_fingerprint"),
    )

    learner_id: UUID = Field(index=True, nullable=False)
    roadmap_id: UUID | None = Field(
        default=None, foreign_key="roadmaps.id", ondelete="SET NULL", nullable=True
    )
    goal_title: str = Field(max_length=200, nullable=False)
    title: str = Field(max_length=220, nullable=False)
    description: str = Field(nullable=False)
    difficulty: Difficulty = Field(sa_column=enum_column(Difficulty))
    estimated_hours: Decimal = Field(sa_column=Column(Numeric(7, 2), nullable=False))
    requirements: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    deliverables: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    acceptance_criteria: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    status: ProjectStatus = Field(
        default=ProjectStatus.PROPOSED, sa_column=enum_column(ProjectStatus)
    )
    request_fingerprint: str = Field(max_length=64, nullable=False)
    generation_prompt_version_id: UUID = Field(
        foreign_key="prompt_versions.id", ondelete="RESTRICT", nullable=False
    )

    roadmap: Roadmap | None = Relationship(
        sa_relationship=relationship("Roadmap", back_populates="projects")
    )
    skills: list[ProjectSkill] = Relationship(
        sa_relationship=relationship(
            "ProjectSkill", back_populates="project", cascade="all, delete-orphan"
        )
    )


class ProjectSkill(UUIDPrimaryKey, table=True):
    """Ordered normalized skill snapshot associated with a project."""

    __tablename__ = "project_skills"
    __table_args__ = (
        UniqueConstraint("project_id", "order_index", name="uq_project_skill_order"),
        UniqueConstraint("project_id", "skill_name", name="uq_project_skill_name"),
        CheckConstraint("order_index >= 0", name="ck_project_skill_order_nonnegative"),
    )

    project_id: UUID = Field(foreign_key="projects.id", ondelete="CASCADE", nullable=False)
    roadmap_skill_id: UUID | None = Field(
        default=None, foreign_key="skills.id", ondelete="SET NULL", nullable=True
    )
    skill_name: str = Field(max_length=160, nullable=False)
    order_index: int = Field(nullable=False)

    project: Project = Relationship(
        sa_relationship=relationship("Project", back_populates="skills")
    )
