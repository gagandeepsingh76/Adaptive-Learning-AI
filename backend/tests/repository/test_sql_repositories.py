"""SQLite repository integration tests."""

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.config.settings import Environment, Settings
from app.core.enums import ExperienceLevel, LearningStyle
from app.database.engine import create_database
from app.models import Conversation, Roadmap
from app.repositories.sql import SQLUnitOfWork


async def test_roadmap_repository_round_trip(tmp_path: Path) -> None:
    database = create_database(
        Settings(
            _env_file=None,
            environment=Environment.TEST,
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'repository.db'}",
        )
    )
    await database.create_schema_for_tests()
    learner_id = uuid4()
    async with SQLUnitOfWork(database.session_factory) as uow:
        prompt = await uow.prompts.get_or_create("roadmap", "1.0.0", "a" * 64, "GeneratedRoadmap")
        roadmap = Roadmap(
            learner_id=learner_id,
            goal_title="Backend Engineer",
            experience_level=ExperienceLevel.BEGINNER,
            learning_style=LearningStyle.MIXED,
            weekly_hours=Decimal("10"),
            estimated_hours=Decimal("100"),
            request_fingerprint="b" * 64,
            generation_prompt_version_id=prompt.id,
        )
        await uow.roadmaps.add(roadmap)
        await uow.commit()

    async with SQLUnitOfWork(database.session_factory) as uow:
        loaded = await uow.roadmaps.get(roadmap.id, learner_id)

    assert loaded is not None
    assert loaded.goal_title == "Backend Engineer"
    await database.dispose()


async def test_conversation_lookup_is_scoped_to_roadmap(tmp_path: Path) -> None:
    database = create_database(
        Settings(
            _env_file=None,
            environment=Environment.TEST,
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'conversation.db'}",
        )
    )
    await database.create_schema_for_tests()
    learner_id = uuid4()
    async with SQLUnitOfWork(database.session_factory) as uow:
        prompt = await uow.prompts.get_or_create("roadmap", "1.0.0", "a" * 64, "GeneratedRoadmap")
        roadmap_a = Roadmap(
            learner_id=learner_id,
            goal_title="Backend Engineer",
            experience_level=ExperienceLevel.BEGINNER,
            learning_style=LearningStyle.MIXED,
            weekly_hours=Decimal("10"),
            estimated_hours=Decimal("100"),
            request_fingerprint="b" * 64,
            generation_prompt_version_id=prompt.id,
        )
        roadmap_b = Roadmap(
            learner_id=learner_id,
            goal_title="AI Engineer",
            experience_level=ExperienceLevel.INTERMEDIATE,
            learning_style=LearningStyle.HANDS_ON,
            weekly_hours=Decimal("8"),
            estimated_hours=Decimal("80"),
            request_fingerprint="c" * 64,
            generation_prompt_version_id=prompt.id,
        )
        await uow.roadmaps.add(roadmap_a)
        await uow.roadmaps.add(roadmap_b)
        conversation = await uow.conversations.add_conversation(
            Conversation(learner_id=learner_id, roadmap_id=roadmap_a.id)
        )
        await uow.commit()

    async with SQLUnitOfWork(database.session_factory) as uow:
        same_roadmap = await uow.conversations.get_conversation(
            conversation.id, learner_id, roadmap_a.id
        )
        other_roadmap = await uow.conversations.get_conversation(
            conversation.id, learner_id, roadmap_b.id
        )

    assert same_roadmap is not None
    assert other_roadmap is None
    await database.dispose()
