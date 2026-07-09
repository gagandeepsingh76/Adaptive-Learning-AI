"""Structured generation recovery tests."""

from app.ai.repair import PromptRepairEngine
from app.ai.structured import StructuredGenerationEngine
from app.core.interfaces.ai import GenerationRequest
from app.core.interfaces.observability import NullAIObservabilitySink
from app.schemas.ai_outputs import FollowUpQuestions
from tests.fixtures.fakes import FakeLLMProvider, FakePromptRenderer, PassingEvaluator


async def test_engine_repairs_invalid_json(ai_cache) -> None:
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
    assert provider.requests[1].prompt_id == "repair"

