"""Persistent response and embedding caches."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, Column, Index, LargeBinary, Numeric, UniqueConstraint
from sqlmodel import Field

from app.core.enums import CacheNamespace
from app.models.base import UUIDPrimaryKey, enum_column
from app.utils.time import utc_now


class ResponseCache(UUIDPrimaryKey, table=True):
    """Validated generated response cache entry."""

    __tablename__ = "response_cache"
    __table_args__ = (
        UniqueConstraint("namespace", "cache_key", name="uq_response_cache_key"),
        CheckConstraint("hit_count >= 0", name="ck_response_cache_hits"),
        Index("ix_response_cache_expires", "expires_at"),
    )

    learner_id: UUID | None = Field(default=None, index=True, nullable=True)
    namespace: CacheNamespace = Field(sa_column=enum_column(CacheNamespace))
    cache_key: str = Field(max_length=64, nullable=False)
    request_hash: str = Field(max_length=64, nullable=False)
    model_name: str = Field(max_length=120, nullable=False)
    prompt_version_id: UUID | None = Field(
        default=None, foreign_key="prompt_versions.id", ondelete="RESTRICT", nullable=True
    )
    schema_version: str = Field(max_length=40, nullable=False)
    response_json: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    quality_score: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(5, 4), nullable=True)
    )
    expires_at: datetime = Field(nullable=False)
    hit_count: int = Field(default=0, nullable=False)
    last_accessed_at: datetime | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class EmbeddingCache(UUIDPrimaryKey, table=True):
    """Content-addressed binary embedding cache."""

    __tablename__ = "embedding_cache"
    __table_args__ = (
        UniqueConstraint(
            "content_hash",
            "model_name",
            "dimensions",
            "task_type",
            name="uq_embedding_cache_identity",
        ),
        CheckConstraint("dimensions > 0", name="ck_embedding_dimensions_positive"),
        CheckConstraint("hit_count >= 0", name="ck_embedding_cache_hits"),
    )

    content_hash: str = Field(max_length=64, nullable=False)
    model_name: str = Field(max_length=120, nullable=False)
    dimensions: int = Field(nullable=False)
    task_type: str = Field(max_length=32, nullable=False)
    vector_bytes: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    last_accessed_at: datetime | None = Field(default=None, nullable=True)
    hit_count: int = Field(default=0, nullable=False)
