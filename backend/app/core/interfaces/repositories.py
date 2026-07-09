"""Persistence-only contracts consumed by business services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from types import TracebackType
from uuid import UUID

from app.models import (
    Conversation,
    LearningResource,
    Message,
    ProgressRecord,
    Project,
    PromptVersion,
    Roadmap,
)


class RoadmapRepository(ABC):
    @abstractmethod
    async def add(self, roadmap: Roadmap) -> Roadmap: ...

    @abstractmethod
    async def get(self, roadmap_id: UUID, learner_id: UUID) -> Roadmap | None: ...


class ProjectRepository(ABC):
    @abstractmethod
    async def add(self, project: Project) -> Project: ...


class ConversationRepository(ABC):
    @abstractmethod
    async def add_conversation(self, conversation: Conversation) -> Conversation: ...

    @abstractmethod
    async def get_conversation(
        self, conversation_id: UUID, learner_id: UUID, roadmap_id: UUID
    ) -> Conversation | None: ...

    @abstractmethod
    async def add_message(self, message: Message) -> Message: ...

    @abstractmethod
    async def get_message(self, message_id: UUID) -> Message | None: ...

    @abstractmethod
    async def recent_messages(self, conversation_id: UUID, limit: int) -> Sequence[Message]: ...


class ProgressRepository(ABC):
    @abstractmethod
    async def get_by_scope(
        self, learner_id: UUID, roadmap_id: UUID, scope_key: str
    ) -> ProgressRecord | None: ...

    @abstractmethod
    async def add(self, record: ProgressRecord) -> ProgressRecord: ...

    @abstractmethod
    async def list_for_roadmap(
        self, learner_id: UUID, roadmap_id: UUID
    ) -> Sequence[ProgressRecord]: ...


class ResourceRepository(ABC):
    @abstractmethod
    async def add_many(self, resources: Sequence[LearningResource]) -> None: ...

    @abstractmethod
    async def list_for_roadmap(
        self, learner_id: UUID, roadmap_id: UUID
    ) -> Sequence[LearningResource]: ...


class PromptVersionRepository(ABC):
    @abstractmethod
    async def get_or_create(
        self, prompt_name: str, version: str, checksum: str, response_schema: str
    ) -> PromptVersion: ...


class UnitOfWork(ABC):
    roadmaps: RoadmapRepository
    projects: ProjectRepository
    conversations: ConversationRepository
    progress: ProgressRepository
    resources: ResourceRepository
    prompts: PromptVersionRepository

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def flush(self) -> None: ...
