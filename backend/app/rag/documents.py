"""Provider-independent RAG document and chunk models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.enums import EntityType
from app.schemas.ai_outputs import GeneratedRoadmap
from app.utils.time import utc_now

MetadataValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class RAGDocument:
    """One semantic entity document before chunking and embedding.

    The UUID provides idempotency; source resolves provenance; embedding and prompt versions
    prevent mixed vector spaces; timestamps support freshness; metadata supports scoped retrieval.
    """

    id: UUID
    content: str
    metadata: Mapping[str, MetadataValue]
    source: str
    entity_type: EntityType
    entity_id: UUID
    parent_id: UUID | None
    embedding_version: str
    prompt_version: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RAGChunk:
    """Semantic document fragment preserving hierarchy and version lineage."""

    id: UUID
    document_id: UUID
    content: str
    metadata: Mapping[str, MetadataValue]
    source: str
    entity_type: EntityType
    entity_id: UUID
    parent_id: UUID | None
    embedding_version: str
    prompt_version: str
    created_at: datetime
    chunk_index: int
    chunk_count: int


class RoadmapDocumentFactory:
    """Decompose a validated roadmap into skill, task, and subtask documents."""

    def create(
        self,
        roadmap: GeneratedRoadmap,
        *,
        roadmap_id: UUID,
        learner_id: UUID,
        content_version: int,
        embedding_version: str,
        prompt_version: str,
        entity_ids: Mapping[str, UUID] | None = None,
        created_at: datetime | None = None,
    ) -> tuple[RAGDocument, ...]:
        timestamp = created_at or utc_now()
        ids = entity_ids or {}
        documents: list[RAGDocument] = []
        for skill in roadmap.skills:
            skill_path = f"skill:{skill.order_index}"
            skill_id = ids.get(skill_path) or _stable_entity_id(roadmap_id, skill_path)
            skill_content = (
                f"Goal: {roadmap.goal_title}\n"
                f"Skill: {skill.title}\n"
                f"Description: {skill.description}\n"
                f"Target proficiency: {skill.target_proficiency}\n"
                f"Estimated hours: {skill.estimated_hours}"
            )
            documents.append(
                self._document(
                    content=skill_content,
                    roadmap_id=roadmap_id,
                    learner_id=learner_id,
                    entity_type=EntityType.SKILL,
                    entity_id=skill_id,
                    parent_id=roadmap_id,
                    order_index=skill.order_index,
                    content_version=content_version,
                    embedding_version=embedding_version,
                    prompt_version=prompt_version,
                    timestamp=timestamp,
                )
            )
            for task in skill.tasks:
                task_path = f"{skill_path}/task:{task.order_index}"
                task_id = ids.get(task_path) or _stable_entity_id(roadmap_id, task_path)
                outcomes = "; ".join(task.learning_outcomes)
                task_content = (
                    f"Goal: {roadmap.goal_title}\n"
                    f"Skill: {skill.title}\n"
                    f"Task: {task.title}\n"
                    f"Description: {task.description}\n"
                    f"Learning outcomes: {outcomes}\n"
                    f"Difficulty: {task.difficulty.value}\n"
                    f"Estimated hours: {task.estimated_hours}"
                )
                documents.append(
                    self._document(
                        content=task_content,
                        roadmap_id=roadmap_id,
                        learner_id=learner_id,
                        entity_type=EntityType.TASK,
                        entity_id=task_id,
                        parent_id=skill_id,
                        order_index=task.order_index,
                        content_version=content_version,
                        embedding_version=embedding_version,
                        prompt_version=prompt_version,
                        timestamp=timestamp,
                        extra_metadata={"skill_id": str(skill_id)},
                    )
                )
                for subtask in task.subtasks:
                    subtask_path = f"{task_path}/subtask:{subtask.order_index}"
                    subtask_id = ids.get(subtask_path) or _stable_entity_id(
                        roadmap_id, subtask_path
                    )
                    subtask_content = (
                        f"Goal: {roadmap.goal_title}\n"
                        f"Skill: {skill.title}\n"
                        f"Task: {task.title}\n"
                        f"Subtask: {subtask.title}\n"
                        f"Action: {subtask.description}\n"
                        f"Completion criteria: {subtask.completion_criteria}\n"
                        f"Estimated hours: {subtask.estimated_hours}"
                    )
                    documents.append(
                        self._document(
                            content=subtask_content,
                            roadmap_id=roadmap_id,
                            learner_id=learner_id,
                            entity_type=EntityType.SUBTASK,
                            entity_id=subtask_id,
                            parent_id=task_id,
                            order_index=subtask.order_index,
                            content_version=content_version,
                            embedding_version=embedding_version,
                            prompt_version=prompt_version,
                            timestamp=timestamp,
                            extra_metadata={
                                "skill_id": str(skill_id),
                                "task_id": str(task_id),
                            },
                        )
                    )
        return tuple(documents)

    @staticmethod
    def _document(
        *,
        content: str,
        roadmap_id: UUID,
        learner_id: UUID,
        entity_type: EntityType,
        entity_id: UUID,
        parent_id: UUID,
        order_index: int,
        content_version: int,
        embedding_version: str,
        prompt_version: str,
        timestamp: datetime,
        extra_metadata: Mapping[str, MetadataValue] | None = None,
    ) -> RAGDocument:
        metadata: dict[str, MetadataValue] = {
            "learner_id": str(learner_id),
            "roadmap_id": str(roadmap_id),
            "entity_type": entity_type.value,
            "entity_id": str(entity_id),
            "parent_id": str(parent_id),
            "order_index": order_index,
            "content_version": content_version,
            "embedding_version": embedding_version,
            "prompt_version": prompt_version,
            "created_at_epoch": timestamp.timestamp(),
        }
        metadata.update(extra_metadata or {})
        document_id = uuid5(
            NAMESPACE_URL,
            f"rag:{roadmap_id}:{entity_type.value}:{entity_id}:v{content_version}",
        )
        return RAGDocument(
            id=document_id,
            content=content,
            metadata=metadata,
            source=f"roadmap:{roadmap_id}",
            entity_type=entity_type,
            entity_id=entity_id,
            parent_id=parent_id,
            embedding_version=embedding_version,
            prompt_version=prompt_version,
            created_at=timestamp,
        )


def _stable_entity_id(roadmap_id: UUID, path: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"roadmap:{roadmap_id}:{path}")

