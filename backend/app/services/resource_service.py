"""Skill-matched learning resource recommendation workflow."""

from collections.abc import Callable
from urllib.parse import quote_plus
from uuid import UUID

from app.core.enums import Difficulty, ResourceType
from app.core.interfaces.repositories import UnitOfWork
from app.exceptions import ResourceNotFoundError
from app.models import LearningResource
from app.schemas.resource import LearningResourceResponse
from app.utils.hashing import sha256_text


class LearningResourceService:
    """Create diverse, safe resource discovery links for roadmap skills."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def recommend(
        self, learner_id: UUID, roadmap_id: UUID
    ) -> list[LearningResourceResponse]:
        async with self._uow_factory() as uow:
            roadmap = await uow.roadmaps.get(roadmap_id, learner_id)
            if roadmap is None:
                raise ResourceNotFoundError("Roadmap was not found.")
            existing = await uow.resources.list_for_roadmap(learner_id, roadmap_id)
            if not existing:
                resources = [
                    resource
                    for skill in roadmap.skills
                    for resource in self._for_skill(learner_id, roadmap_id, skill.id, skill.title)
                ]
                await uow.resources.add_many(resources)
                await uow.commit()
                existing = resources
        return [
            LearningResourceResponse(
                id=item.id,
                skill_id=item.skill_id,
                title=item.title,
                url=item.url,
                provider=item.provider,
                resource_type=item.resource_type,
                description=item.description,
                recommendation_reason=item.recommendation_reason,
            )
            for item in existing
        ]

    @staticmethod
    def _for_skill(
        learner_id: UUID, roadmap_id: UUID, skill_id: UUID, skill: str
    ) -> list[LearningResource]:
        query = quote_plus(skill)
        definitions = (
            ("Official documentation", "Official Docs", ResourceType.DOCUMENTATION, f"https://devdocs.io/#q={query}"),
            ("Books", "O'Reilly", ResourceType.BOOK, f"https://www.oreilly.com/search/?q={query}"),
            ("Courses", "Coursera", ResourceType.COURSE, f"https://www.coursera.org/search?query={query}"),
            ("YouTube lessons", "YouTube", ResourceType.VIDEO, f"https://www.youtube.com/results?search_query={query}"),
            ("Engineering articles", "DEV Community", ResourceType.ARTICLE, f"https://dev.to/search?q={query}"),
        )
        return [
            LearningResource(
                learner_id=learner_id,
                roadmap_id=roadmap_id,
                skill_id=skill_id,
                title=f"{title}: {skill}",
                url=url,
                url_hash=sha256_text(url),
                provider=provider,
                resource_type=resource_type,
                description=f"Discover current {provider} material for {skill}.",
                difficulty=Difficulty.INTERMEDIATE,
                recommendation_reason=f"Directly supports the roadmap skill {skill}.",
            )
            for title, provider, resource_type, url in definitions
        ]
