"""Generation quality audit model."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, Column, Index, Numeric
from sqlmodel import Field

from app.core.enums import EntityType
from app.models.base import UUIDPrimaryKey, enum_column
from app.utils.time import utc_now


class GenerationEvaluation(UUIDPrimaryKey, table=True):
    """Immutable quality-gate result for one generation attempt."""

    __tablename__ = "generation_evaluations"
    __table_args__ = (
        CheckConstraint("attempt_number >= 1", name="ck_evaluation_attempt_positive"),
        CheckConstraint(
            "weighted_score >= 0 AND weighted_score <= 1",
            name="ck_evaluation_weighted_score",
        ),
        Index("ix_evaluation_entity", "entity_type", "entity_id"),
        Index("ix_evaluation_fingerprint", "request_fingerprint"),
    )

    entity_type: EntityType = Field(sa_column=enum_column(EntityType))
    entity_id: UUID | None = Field(default=None, nullable=True)
    request_fingerprint: str = Field(max_length=64, nullable=False)
    attempt_number: int = Field(nullable=False)
    completeness_score: Decimal = Field(sa_column=Column(Numeric(5, 4), nullable=False))
    personalization_score: Decimal = Field(sa_column=Column(Numeric(5, 4), nullable=False))
    logical_ordering_score: Decimal = Field(sa_column=Column(Numeric(5, 4), nullable=False))
    skill_progression_score: Decimal = Field(sa_column=Column(Numeric(5, 4), nullable=False))
    duplicate_avoidance_score: Decimal = Field(sa_column=Column(Numeric(5, 4), nullable=False))
    hour_consistency_score: Decimal = Field(sa_column=Column(Numeric(5, 4), nullable=False))
    json_correctness_score: Decimal = Field(sa_column=Column(Numeric(5, 4), nullable=False))
    weighted_score: Decimal = Field(sa_column=Column(Numeric(5, 4), nullable=False))
    hard_failures: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    feedback: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    evaluator_prompt_version_id: UUID | None = Field(
        default=None, foreign_key="prompt_versions.id", ondelete="RESTRICT", nullable=True
    )
    evaluator_model: str | None = Field(default=None, max_length=120, nullable=True)
    passed: bool = Field(nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
