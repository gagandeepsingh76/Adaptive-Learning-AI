"""Conversation and message persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, Column, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship

from app.core.enums import ConversationStatus, MessageRole, ProcessingStatus
from app.models.base import TimestampedModel, UUIDPrimaryKey, enum_column
from app.utils.time import utc_now

if TYPE_CHECKING:
    from app.models.roadmap import Roadmap


class Conversation(UUIDPrimaryKey, TimestampedModel, table=True):
    """Ordered learner chat scoped to one roadmap."""

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("id", "learner_id", name="uq_conversation_id_learner"),
        CheckConstraint("next_sequence >= 1", name="ck_conversation_next_sequence"),
        Index("ix_conversation_learner_recent", "learner_id", "last_message_at"),
        Index("ix_conversation_roadmap_recent", "roadmap_id", "last_message_at"),
    )

    learner_id: UUID = Field(index=True, nullable=False)
    roadmap_id: UUID = Field(foreign_key="roadmaps.id", ondelete="CASCADE", nullable=False)
    title: str | None = Field(default=None, max_length=200, nullable=True)
    status: ConversationStatus = Field(
        default=ConversationStatus.ACTIVE, sa_column=enum_column(ConversationStatus)
    )
    next_sequence: int = Field(default=1, nullable=False)
    last_message_at: datetime | None = Field(default=None, nullable=True)

    roadmap: Roadmap = Relationship(
        sa_relationship=relationship("Roadmap", back_populates="conversations")
    )
    messages: list[Message] = Relationship(
        sa_relationship=relationship(
            "Message", back_populates="conversation", cascade="all, delete-orphan"
        )
    )


class Message(UUIDPrimaryKey, table=True):
    """Immutable conversation turn and its generation audit metadata."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence_number", name="uq_message_sequence"),
        CheckConstraint("sequence_number >= 1", name="ck_message_sequence_positive"),
        CheckConstraint(
            "prompt_tokens IS NULL OR prompt_tokens >= 0", name="ck_message_prompt_tokens"
        ),
        CheckConstraint(
            "completion_tokens IS NULL OR completion_tokens >= 0",
            name="ck_message_completion_tokens",
        ),
        Index("ix_message_conversation_created", "conversation_id", "created_at"),
    )

    conversation_id: UUID = Field(
        foreign_key="conversations.id", ondelete="CASCADE", nullable=False
    )
    sequence_number: int = Field(nullable=False)
    role: MessageRole = Field(sa_column=enum_column(MessageRole))
    content: str = Field(nullable=False)
    processing_status: ProcessingStatus = Field(sa_column=enum_column(ProcessingStatus))
    source_citations: list[dict[str, Any]] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    retrieval_summary: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    model_name: str | None = Field(default=None, max_length=120, nullable=True)
    prompt_version_id: UUID | None = Field(
        default=None, foreign_key="prompt_versions.id", ondelete="RESTRICT", nullable=True
    )
    prompt_tokens: int | None = Field(default=None, nullable=True)
    completion_tokens: int | None = Field(default=None, nullable=True)
    error_code: str | None = Field(default=None, max_length=80, nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)

    conversation: Conversation = Relationship(
        sa_relationship=relationship("Conversation", back_populates="messages")
    )
