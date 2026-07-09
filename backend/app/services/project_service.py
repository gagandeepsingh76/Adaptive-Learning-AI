"""Project recommendation business workflow."""

from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from app.ai.structured import StructuredGenerationEngine
from app.core.interfaces.ai import GenerationRequest, PromptRenderer
from app.core.interfaces.repositories import UnitOfWork
from app.exceptions import ResourceNotFoundError
from app.models import Project, ProjectSkill
from app.schemas.ai_outputs import GeneratedProject
from app.schemas.project import ProjectCreateRequest, ProjectResponse
from app.utils.hashing import fingerprint


class ProjectService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        prompts: PromptRenderer,
        generator: StructuredGenerationEngine,
    ) -> None:
        self._uow_factory = uow_factory
        self._prompts = prompts
        self._generator = generator

    async def create(
        self, learner_id: UUID, command: ProjectCreateRequest, request_id: str | None = None
    ) -> ProjectResponse:
        roadmap = None
        if command.roadmap_id is not None:
            async with self._uow_factory() as uow:
                roadmap = await uow.roadmaps.get(command.roadmap_id, learner_id)
            if roadmap is None:
                raise ResourceNotFoundError("Roadmap was not found.")
            goal_title = roadmap.goal_title
            skills = [skill.title for skill in roadmap.skills]
        else:
            goal_title = command.goal_title or ""
            skills = command.skills or []
        rendered = await self._prompts.render(
            "project",
            {
                "source": {"goal_title": goal_title, "skills": skills},
                "constraints": {
                    "difficulty": command.difficulty.value,
                    "additional": command.constraints,
                },
            },
        )
        generated = await self._generator.generate(
            GenerationRequest(
                prompt=rendered.text,
                prompt_id=rendered.prompt_id,
                prompt_version=rendered.version,
                request_id=request_id,
                roadmap_id=str(command.roadmap_id) if command.roadmap_id else None,
            ),
            GeneratedProject,
            quality_context={"goal_title": goal_title, "skills": skills},
        )
        async with self._uow_factory() as uow:
            prompt = await uow.prompts.get_or_create(
                rendered.prompt_id, rendered.version, rendered.prompt_hash, "GeneratedProject"
            )
            project = Project(
                learner_id=learner_id,
                roadmap_id=command.roadmap_id,
                goal_title=goal_title,
                title=generated.title,
                description=generated.description,
                difficulty=generated.difficulty,
                estimated_hours=Decimal(str(generated.estimated_hours)),
                requirements=generated.requirements,
                deliverables=generated.deliverables,
                acceptance_criteria=generated.acceptance_criteria,
                request_fingerprint=fingerprint(command.model_dump(mode="json")),
                generation_prompt_version_id=prompt.id,
            )
            for index, skill_name in enumerate(generated.skills):
                roadmap_skill = next(
                    (skill for skill in roadmap.skills if skill.title == skill_name), None
                ) if roadmap else None
                project.skills.append(
                    ProjectSkill(
                        project_id=project.id,
                        roadmap_skill_id=roadmap_skill.id if roadmap_skill else None,
                        skill_name=skill_name,
                        order_index=index,
                    )
                )
            await uow.projects.add(project)
            await uow.commit()
        return ProjectResponse(
            project_id=project.id,
            roadmap_id=project.roadmap_id,
            title=project.title,
            description=project.description,
            difficulty=project.difficulty,
            estimated_hours=project.estimated_hours,
            skills=[skill.skill_name for skill in project.skills],
            requirements=project.requirements,
            deliverables=project.deliverables,
            acceptance_criteria=project.acceptance_criteria,
        )

