"""Structured generation recovery tests."""

import json

from app.ai.cache import SQLiteAICache
from app.ai.repair import PromptRepairEngine
from app.ai.structured import StructuredGenerationEngine
from app.core.interfaces.ai import GenerationRequest
from app.core.interfaces.observability import NullAIObservabilitySink
from app.schemas.ai_outputs import FollowUpQuestions, GeneratedRoadmap
from app.utils.hashing import fingerprint
from tests.fixtures.fakes import FakeLLMProvider, FakePromptRenderer, PassingEvaluator
from tests.unit.test_validation import valid_roadmap


async def test_engine_retries_invalid_json_once_with_validation_errors(
    ai_cache: SQLiteAICache,
) -> None:
    provider = FakeLLMProvider(
        ["not-json", '{"questions":["What should I build?","How do I verify it?"]}']
    )
    repair = PromptRepairEngine(provider, FakePromptRenderer())
    engine = StructuredGenerationEngine(
        provider,
        repair,
        PassingEvaluator(),
        ai_cache,
        NullAIObservabilitySink(),
    )

    result = await engine.generate(
        GenerationRequest(prompt="Generate follow-ups", prompt_id="follow_up"),
        FollowUpQuestions,
    )

    assert len(result.questions) == 2
    assert len(provider.requests) == 2
    assert provider.requests[0].response_schema == {"type": "object"}
    assert "<json_output_contract>" in provider.requests[0].prompt
    assert provider.requests[1].prompt_id == "follow_up"
    assert provider.requests[1].prompt_version == "unversioned+repair.1"
    assert "<generation_clarifications>" in provider.requests[1].prompt
    assert "Expecting value" in provider.requests[1].prompt


async def test_engine_regenerates_invalid_cached_roadmap(ai_cache: SQLiteAICache) -> None:
    request = GenerationRequest(
        prompt="Generate a roadmap",
        prompt_id="roadmap",
        prompt_version="1.0.0",
    )
    invalid_cached = valid_roadmap()
    invalid_cached["skills"][0]["tasks"][0]["difficulty"] = "medium"  # type: ignore[index]
    cache_key = fingerprint(
        {
            "prompt": request.prompt,
            "prompt_id": request.prompt_id,
            "prompt_version": request.prompt_version,
            "model": request.model,
            "schema": GeneratedRoadmap.model_json_schema(),
        }
    )
    await ai_cache.set("structured_generation", cache_key, invalid_cached, 60)
    provider = FakeLLMProvider([json.dumps(valid_roadmap())])
    repair = PromptRepairEngine(provider, FakePromptRenderer())
    engine = StructuredGenerationEngine(
        provider,
        repair,
        PassingEvaluator(),
        ai_cache,
        NullAIObservabilitySink(),
    )

    result = await engine.generate(request, GeneratedRoadmap, validate_quality=False)

    assert result.skills[0].tasks[0].difficulty == "beginner"
    assert len(provider.requests) == 1
    assert provider.requests[0].response_schema == {"type": "object"}
    assert "<json_output_contract>" in provider.requests[0].prompt
    assert "$defs" not in provider.requests[0].prompt
