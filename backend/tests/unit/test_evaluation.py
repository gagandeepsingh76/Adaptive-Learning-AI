"""Generation quality evaluator tests."""

import json

from app.ai.evaluation import GenerationEvaluator
from app.ai.validation import ResponseValidator
from app.schemas.ai_outputs import GeneratedRoadmap
from tests.unit.test_validation import valid_roadmap


async def test_deterministic_evaluator_scores_all_dimensions(ai_cache) -> None:
    candidate = ResponseValidator(GeneratedRoadmap).validate_json(json.dumps(valid_roadmap()))
    evaluator = GenerationEvaluator(0.75, ai_cache)

    result = await evaluator.evaluate(candidate, {"experience": "beginner"})

    assert result.passed
    assert len(result.dimension_scores) == 10
    assert result.dimension_scores["personalization"] == 0.9

