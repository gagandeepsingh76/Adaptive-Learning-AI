"""Prompt version registry model."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Column, Index, UniqueConstraint
from sqlmodel import Field

from app.core.enums import PromptStatus
from app.models.base import UUIDPrimaryKey, enum_column
from app.utils.time import utc_now


class PromptVersion(UUIDPrimaryKey, table=True):
    """Immutable registry entry for one reviewed prompt asset."""

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("prompt_name", "version", name="uq_prompt_name_version"),
        CheckConstraint("version >= 1", name="ck_prompt_version_positive"),
        Index("ix_prompt_name_status", "prompt_name", "status"),
    )

    prompt_name: str = Field(max_length=80, nullable=False)
    version: int = Field(nullable=False)
    template_checksum: str = Field(max_length=64, nullable=False)
    variables_schema: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    response_schema_name: str = Field(max_length=160, nullable=False)
    status: PromptStatus = Field(
        default=PromptStatus.ACTIVE, sa_column=enum_column(PromptStatus)
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    activated_at: datetime | None = Field(default=None, nullable=True)
