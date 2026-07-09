"""Async SQLModel repository implementations without business logic."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from types import TracebackType
from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.enums import PromptStatus
from app.core.interfaces.repositories import (
    ConversationRepository,
    ProgressRepository,
    ProjectRepository,
    PromptVersionRepository,
    ResourceRepository,
    RoadmapRepository,
    UnitOfWork,
)
from app.models import (
    Conversation,
    LearningResource,
    Message,
    ProgressRecord,
    Project,
    PromptVersion,
    Roadmap,
    Skill,
    Task,
)


class SQLRoadmapRepository(RoadmapRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, roadmap: Roadmap) -> Roadmap:
        self._session.add(roadmap)
        await self._session.flush()
        return roadmap

    async def get(self, roadmap_id: UUID, learner_id: UUID) -> Roadmap | None:
        statement = (
            select(Roadmap)
            .where(Roadmap.id == roadmap_id, Roadmap.learner_id == learner_id)
            .options(
                selectinload(cast(Any, Roadmap.skills))
                .selectinload(cast(Any, Skill.tasks))
                .selectinload(cast(Any, Task.subtasks))
            )
        )
        return (await self._session.exec(statement)).one_or_none()


class SQLProjectRepository(ProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, project: Project) -> Project:
        self._session.add(project)
        await self._session.flush()
        return project


class SQLConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_conversation(self, conversation: Conversation) -> Conversation:
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get_conversation(
        self, conversation_id: UUID, learner_id: UUID, roadmap_id: UUID
    ) -> Conversation | None:
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.learner_id == learner_id,
            Conversation.roadmap_id == roadmap_id,
        )
        return (await self._session.exec(statement)).one_or_none()

    async def add_message(self, message: Message) -> Message:
        self._session.add(message)
        await self._session.flush()
        return message

    async def get_message(self, message_id: UUID) -> Message | None:
        return await self._session.get(Message, message_id)

    async def recent_messages(self, conversation_id: UUID, limit: int) -> Sequence[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(cast(Any, Message.sequence_number).desc())
            .limit(limit)
        )
        return tuple(reversed((await self._session.exec(statement)).all()))


class SQLProgressRepository(ProgressRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_scope(
        self, learner_id: UUID, roadmap_id: UUID, scope_key: str
    ) -> ProgressRecord | None:
        statement = select(ProgressRecord).where(
            ProgressRecord.learner_id == learner_id,
            ProgressRecord.roadmap_id == roadmap_id,
            ProgressRecord.scope_key == scope_key,
        )
        return (await self._session.exec(statement)).one_or_none()

    async def add(self, record: ProgressRecord) -> ProgressRecord:
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_for_roadmap(
        self, learner_id: UUID, roadmap_id: UUID
    ) -> Sequence[ProgressRecord]:
        statement = select(ProgressRecord).where(
            ProgressRecord.learner_id == learner_id,
            ProgressRecord.roadmap_id == roadmap_id,
        )
        return (await self._session.exec(statement)).all()


class SQLResourceRepository(ResourceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, resources: Sequence[LearningResource]) -> None:
        self._session.add_all(resources)
        await self._session.flush()

    async def list_for_roadmap(
        self, learner_id: UUID, roadmap_id: UUID
    ) -> Sequence[LearningResource]:
        statement = select(LearningResource).where(
            LearningResource.learner_id == learner_id,
            LearningResource.roadmap_id == roadmap_id,
        )
        return (await self._session.exec(statement)).all()


class SQLPromptVersionRepository(PromptVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(
        self, prompt_name: str, version: str, checksum: str, response_schema: str
    ) -> PromptVersion:
        numeric_version = int(version.split(".")[0])
        statement = select(PromptVersion).where(
            PromptVersion.prompt_name == prompt_name,
            PromptVersion.version == numeric_version,
        )
        existing = (await self._session.exec(statement)).one_or_none()
        if existing is not None:
            return existing
        prompt = PromptVersion(
            prompt_name=prompt_name,
            version=numeric_version,
            template_checksum=checksum,
            variables_schema={},
            response_schema_name=response_schema,
            status=PromptStatus.ACTIVE,
        )
        self._session.add(prompt)
        await self._session.flush()
        return prompt


class SQLUnitOfWork(UnitOfWork):
    """Request-independent transaction boundary created by a factory."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SQLUnitOfWork:
        self._session = self._session_factory()
        self.roadmaps = SQLRoadmapRepository(self._session)
        self.projects = SQLProjectRepository(self._session)
        self.conversations = SQLConversationRepository(self._session)
        self.progress = SQLProgressRepository(self._session)
        self.resources = SQLResourceRepository(self._session)
        self.prompts = SQLPromptVersionRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc, traceback
        if self._session is None:
            return
        if exc_type is not None:
            await self._session.rollback()
        await self._session.close()

    async def commit(self) -> None:
        await self._require_session().commit()

    async def flush(self) -> None:
        await self._require_session().flush()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active")
        return self._session


type UnitOfWorkFactory = Callable[[], SQLUnitOfWork]


def unit_of_work_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> UnitOfWorkFactory:
    return lambda: SQLUnitOfWork(session_factory)
