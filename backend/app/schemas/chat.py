"""RAG chat API contracts."""

from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.schemas.common import StrictSchema


class ChatRequest(StrictSchema):
    roadmap_id: UUID
    question: Annotated[str, Field(min_length=2, max_length=4000)]
    conversation_id: UUID | None = None


class CitationResponse(StrictSchema):
    source_id: str
    entity_type: str
    entity_id: str
    relevance: float


class ChatResponse(StrictSchema):
    conversation_id: UUID
    message_id: UUID
    answer: str
    citations: list[CitationResponse]
    follow_up_questions: list[str]

