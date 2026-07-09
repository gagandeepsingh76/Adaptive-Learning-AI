"""Progress API contracts."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.core.enums import ProgressStatus, ProgressTargetType
from app.schemas.common import StrictSchema


class ProgressUpdateRequest(StrictSchema):
    target_type: ProgressTargetType
    target_id: UUID | None = None
    status: ProgressStatus
    progress_percent: Annotated[Decimal, Field(ge=0, le=100)]
    time_spent_minutes: Annotated[int, Field(ge=0)] = 0
    notes: Annotated[str | None, Field(max_length=2000)] = None


class ProgressItemResponse(StrictSchema):
    target_type: ProgressTargetType
    target_id: UUID
    status: ProgressStatus
    progress_percent: Decimal
    time_spent_minutes: int


class ProgressSummaryResponse(StrictSchema):
    roadmap_id: UUID
    completion_percentage: Decimal
    total_subtasks: int
    completed_subtasks: int
    total_time_spent_minutes: int
    records: list[ProgressItemResponse]
