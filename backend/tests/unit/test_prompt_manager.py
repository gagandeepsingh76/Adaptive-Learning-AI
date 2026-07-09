"""Prompt asset validation and rendering tests."""

from pathlib import Path

import pytest

from app.ai.cache import SQLiteAICache
from app.exceptions import PromptConfigurationError
from app.prompts.manager import PromptManager

PROMPT_ROOT = Path(__file__).parents[2] / "app" / "prompts" / "templates"


async def test_prompt_manager_renders_and_fingerprints(ai_cache: SQLiteAICache) -> None:
    manager = PromptManager(PROMPT_ROOT, ai_cache)
    variables = {"goal": "Backend Engineer", "learner_profile": {}, "constraints": {}}

    first = await manager.render("roadmap", variables)
    second = await manager.render("roadmap", variables)

    assert first == second
    assert first.version == "1.0.0"
    assert "Backend Engineer" in first.text
    assert len(first.prompt_hash) == 64


async def test_prompt_manager_rejects_variable_drift(ai_cache: SQLiteAICache) -> None:
    manager = PromptManager(PROMPT_ROOT, ai_cache)

    with pytest.raises(PromptConfigurationError):
        await manager.render("roadmap", {"goal": "AI Engineer"})

