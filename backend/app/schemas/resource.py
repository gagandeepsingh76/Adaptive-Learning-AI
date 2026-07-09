"""Learning-resource business responses."""

from uuid import UUID

from pydantic import HttpUrl

from app.core.enums import ResourceType
from app.schemas.common import StrictSchema


class LearningResourceResponse(StrictSchema):
    id: UUID
    skill_id: UUID | None
    title: str
    url: HttpUrl
    provider: str
    resource_type: ResourceType
    description: str
    recommendation_reason: str

