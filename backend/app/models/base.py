"""Reusable SQLModel persistence fields."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.utils.time import utc_now


class UUIDPrimaryKey(SQLModel):
    """UUID identity shared by all persisted entities."""

    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)


class TimestampedModel(SQLModel):
    """Creation and last-update timestamps managed by repositories."""

    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


def enum_column(enum_type: type[StrEnum], *, nullable: bool = False) -> Column[Any]:
    """Create a portable string-backed enum column without native database enums."""
    max_length = max(len(member.value) for member in enum_type)
    return Column(
        SAEnum(
            enum_type,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda members: [member.value for member in members],
            length=max_length,
        ),
        nullable=nullable,
    )
