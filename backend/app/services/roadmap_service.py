"""Complete roadmap generation, persistence, and indexing use case."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from app.ai.structured import StructuredGenerationEngine
from app.core.enums import IndexStatus
from app.core.interfaces.ai import GenerationRequest, PromptRenderer
from app.core.interfaces.repositories import UnitOfWork
from app.models import Roadmap, Skill, Subtask, Task
from app.rag.documents import RoadmapDocumentFactory
from app.rag.indexer import RAGIndexer
from app.schemas.ai_outputs import GeneratedRoadmap
from app.schemas.roadmap import (
    RoadmapCreateRequest,
    RoadmapResponse,
    SkillResponse,
    SubtaskResponse,
    TaskResponse,
)
from app.utils.hashing import fingerprint


class RoadmapService:
    """Orchestrate the roadmap use case without HTTP or provider dependencies."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        prompts: PromptRenderer,
        generator: StructuredGenerationEngine,
        documents: RoadmapDocumentFactory,
        indexer: RAGIndexer,
        embedding_version: str,
    ) -> None:
        self._uow_factory = uow_factory
        self._prompts = prompts
        self._generator = generator
        self._documents = documents
        self._indexer = indexer
        self._embedding_version = embedding_version

    async def create(
        self, learner_id: UUID, command: RoadmapCreateRequest, request_id: str | None = None
    ) -> RoadmapResponse:
        rendered = await self._prompts.render(
            "roadmap",
            {
                "goal": {
                    "title": command.goal_title,
                    "description": command.goal_description,
                },
                "learner_profile": {
                    "experience": command.experience_level.value,
                    "learning_style": command.learning_style.value,
                    "weekly_hours": str(command.weekly_hours),
                    "existing_skills": command.existing_skills,
                },
                "constraints": command.constraints,
            },
        )
        generated = await self._generator.generate(
            GenerationRequest(
                prompt=rendered.text,
                prompt_id=rendered.prompt_id,
                prompt_version=rendered.version,
                request_id=request_id,
            ),
            GeneratedRoadmap,
            quality_context=command.model_dump(mode="json"),
        )
        entity_ids: dict[str, UUID] = {}
        async with self._uow_factory() as uow:
            prompt = await uow.prompts.get_or_create(
                rendered.prompt_id, rendered.version, rendered.prompt_hash, "GeneratedRoadmap"
            )
            roadmap = self._to_model(learner_id, command, generated, prompt.id, entity_ids)
            await uow.roadmaps.add(roadmap)
            await uow.commit()

        try:
            documents = self._documents.create(
                generated,
                roadmap_id=roadmap.id,
                learner_id=learner_id,
                content_version=roadmap.content_version,
                embedding_version=self._embedding_version,
                prompt_version=rendered.version,
                entity_ids=entity_ids,
            )
            await self._indexer.index(
                documents, request_id=request_id, roadmap_id=str(roadmap.id)
            )
            await self._set_index_state(roadmap.id, learner_id, IndexStatus.READY, 1)
        except Exception:
            await self._set_index_state(roadmap.id, learner_id, IndexStatus.FAILED, None)
            raise
        return self._response(roadmap)

    async def _set_index_state(
        self, roadmap_id: UUID, learner_id: UUID, state: IndexStatus, version: int | None
    ) -> None:
        async with self._uow_factory() as uow:
            roadmap = await uow.roadmaps.get(roadmap_id, learner_id)
            if roadmap is not None:
                roadmap.index_status = state
                roadmap.indexed_content_version = version
                await uow.commit()

    @staticmethod
    def _to_model(
        learner_id: UUID,
        command: RoadmapCreateRequest,
        generated: GeneratedRoadmap,
        prompt_id: UUID,
        entity_ids: dict[str, UUID],
    ) -> Roadmap:
        roadmap = Roadmap(
            learner_id=learner_id,
            goal_title=generated.goal_title,
            goal_description=command.goal_description,
            experience_level=command.experience_level,
            learning_style=command.learning_style,
            weekly_hours=command.weekly_hours,
            estimated_hours=Decimal(str(generated.estimated_hours)),
            request_fingerprint=fingerprint(command.model_dump(mode="json")),
            generation_prompt_version_id=prompt_id,
            index_status=IndexStatus.INDEXING,
        )
        for skill_data in generated.skills:
            skill = Skill(
                roadmap_id=roadmap.id,
                title=skill_data.title,
                description=skill_data.description,
                target_proficiency=skill_data.target_proficiency,
                estimated_hours=Decimal(str(skill_data.estimated_hours)),
                order_index=skill_data.order_index,
            )
            entity_ids[f"skill:{skill_data.order_index}"] = skill.id
            for task_data in skill_data.tasks:
                task = Task(
                    skill_id=skill.id,
                    title=task_data.title,
                    description=task_data.description,
                    difficulty=task_data.difficulty,
                    estimated_hours=Decimal(str(task_data.estimated_hours)),
                    order_index=task_data.order_index,
                    learning_outcomes=task_data.learning_outcomes,
                )
                path = f"skill:{skill_data.order_index}/task:{task_data.order_index}"
                entity_ids[path] = task.id
                for item in task_data.subtasks:
                    subtask = Subtask(
                        task_id=task.id,
                        title=item.title,
                        description=item.description,
                        completion_criteria=item.completion_criteria,
                        estimated_hours=Decimal(str(item.estimated_hours)),
                        order_index=item.order_index,
                    )
                    entity_ids[f"{path}/subtask:{item.order_index}"] = subtask.id
                    task.subtasks.append(subtask)
                skill.tasks.append(task)
            roadmap.skills.append(skill)
        return roadmap

    @staticmethod
    def _response(roadmap: Roadmap) -> RoadmapResponse:
        return RoadmapResponse(
            roadmap_id=roadmap.id,
            goal_title=roadmap.goal_title,
            estimated_hours=roadmap.estimated_hours,
            skills=[
                SkillResponse(
                    id=skill.id,
                    title=skill.title,
                    description=skill.description,
                    target_proficiency=skill.target_proficiency,
                    estimated_hours=skill.estimated_hours,
                    order_index=skill.order_index,
                    tasks=[
                        TaskResponse(
                            id=task.id,
                            title=task.title,
                            description=task.description,
                            difficulty=task.difficulty.value,
                            estimated_hours=task.estimated_hours,
                            order_index=task.order_index,
                            learning_outcomes=task.learning_outcomes,
                            subtasks=[
                                SubtaskResponse(
                                    id=item.id,
                                    title=item.title,
                                    description=item.description,
                                    completion_criteria=item.completion_criteria,
                                    estimated_hours=item.estimated_hours,
                                    order_index=item.order_index,
                                )
                                for item in task.subtasks
                            ],
                        )
                        for task in skill.tasks
                    ],
                )
                for skill in roadmap.skills
            ],
        )
