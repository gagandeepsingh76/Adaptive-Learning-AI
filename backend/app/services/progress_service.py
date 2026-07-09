"""Progress update and roadmap statistics use cases."""

from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from app.core.enums import ProgressStatus, ProgressTargetType
from app.core.interfaces.repositories import UnitOfWork
from app.exceptions import DomainValidationError, ResourceNotFoundError
from app.models import ProgressRecord, Roadmap
from app.schemas.progress import (
    ProgressItemResponse,
    ProgressSummaryResponse,
    ProgressUpdateRequest,
)
from app.utils.time import utc_now


class ProgressService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def update(
        self, learner_id: UUID, roadmap_id: UUID, command: ProgressUpdateRequest
    ) -> ProgressSummaryResponse:
        async with self._uow_factory() as uow:
            roadmap = await uow.roadmaps.get(roadmap_id, learner_id)
            if roadmap is None:
                raise ResourceNotFoundError("Roadmap was not found.")
            target_id = self._validate_target(roadmap, command)
            scope_key = f"{command.target_type.value}:{target_id}"
            record = await uow.progress.get_by_scope(learner_id, roadmap_id, scope_key)
            if record is None:
                record = ProgressRecord(
                    learner_id=learner_id,
                    roadmap_id=roadmap_id,
                    target_type=command.target_type,
                    scope_key=scope_key,
                )
                self._set_target(record, command.target_type, command.target_id)
                await uow.progress.add(record)
            record.status = command.status
            record.progress_percent = command.progress_percent
            record.time_spent_minutes = command.time_spent_minutes
            record.notes = command.notes
            if command.status is ProgressStatus.IN_PROGRESS and record.started_at is None:
                record.started_at = utc_now()
            record.completed_at = (
                utc_now() if command.status is ProgressStatus.COMPLETED else None
            )
            await uow.commit()
        return await self.get_summary(learner_id, roadmap_id)

    async def get_summary(
        self, learner_id: UUID, roadmap_id: UUID
    ) -> ProgressSummaryResponse:
        async with self._uow_factory() as uow:
            roadmap = await uow.roadmaps.get(roadmap_id, learner_id)
            if roadmap is None:
                raise ResourceNotFoundError("Roadmap was not found.")
            records = await uow.progress.list_for_roadmap(learner_id, roadmap_id)
        subtasks = [
            item
            for skill in roadmap.skills
            for task in skill.tasks
            for item in task.subtasks
        ]
        completed_ids = {
            record.subtask_id
            for record in records
            if record.target_type is ProgressTargetType.SUBTASK
            and record.status is ProgressStatus.COMPLETED
        }
        total = len(subtasks)
        completed = sum(item.id in completed_ids for item in subtasks)
        percentage = (
            Decimal("0")
            if total == 0
            else Decimal(completed * 100 / total).quantize(Decimal("0.01"))
        )
        return ProgressSummaryResponse(
            roadmap_id=roadmap_id,
            completion_percentage=percentage,
            total_subtasks=total,
            completed_subtasks=completed,
            total_time_spent_minutes=sum(record.time_spent_minutes for record in records),
            records=[
                ProgressItemResponse(
                    target_type=record.target_type,
                    target_id=UUID(record.scope_key.split(":", 1)[1]),
                    status=record.status,
                    progress_percent=record.progress_percent,
                    time_spent_minutes=record.time_spent_minutes,
                )
                for record in records
            ],
        )

    @staticmethod
    def _validate_target(roadmap: Roadmap, command: ProgressUpdateRequest) -> UUID:
        if command.target_type is ProgressTargetType.ROADMAP:
            if command.target_id not in (None, roadmap.id):
                raise DomainValidationError("Roadmap progress target does not match route.")
            return roadmap.id
        if command.target_id is None:
            raise DomainValidationError("A target_id is required for hierarchy progress.")
        valid_ids = {
            ProgressTargetType.SKILL: {skill.id for skill in roadmap.skills},
            ProgressTargetType.TASK: {
                task.id for skill in roadmap.skills for task in skill.tasks
            },
            ProgressTargetType.SUBTASK: {
                item.id
                for skill in roadmap.skills
                for task in skill.tasks
                for item in task.subtasks
            },
        }[command.target_type]
        if command.target_id not in valid_ids:
            raise DomainValidationError("Progress target does not belong to the roadmap.")
        return command.target_id

    @staticmethod
    def _set_target(
        record: ProgressRecord, target_type: ProgressTargetType, target_id: UUID | None
    ) -> None:
        if target_type is ProgressTargetType.SKILL:
            record.skill_id = target_id
        elif target_type is ProgressTargetType.TASK:
            record.task_id = target_id
        elif target_type is ProgressTargetType.SUBTASK:
            record.subtask_id = target_id
