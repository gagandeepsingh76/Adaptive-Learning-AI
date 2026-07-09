"""Deterministic and optionally model-assisted generation quality evaluation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.interfaces.ai import (
    EvaluationResult,
    GenerationRequest,
    LLMProvider,
    PromptRenderer,
    QualityEvaluator,
)
from app.core.interfaces.cache import AICache
from app.schemas.ai_outputs import EvaluationOutput, GeneratedProject, GeneratedRoadmap
from app.utils.hashing import fingerprint

_DIMENSIONS = (
    "completeness",
    "logical_flow",
    "personalization",
    "progression",
    "coverage",
    "estimated_hours",
    "task_consistency",
    "duplicate_skills",
    "duplicate_tasks",
    "output_quality",
)


class GenerationEvaluator(QualityEvaluator):
    """Cacheable quality gate with deterministic baselines and optional LLM rubric."""

    evaluator_version = "1.0.0"

    def __init__(
        self,
        threshold: float,
        cache: AICache,
        provider: LLMProvider | None = None,
        prompt_renderer: PromptRenderer | None = None,
        cache_ttl_seconds: int = 86_400,
    ) -> None:
        self._threshold = threshold
        self._cache = cache
        self._provider = provider
        self._prompt_renderer = prompt_renderer
        self._cache_ttl_seconds = cache_ttl_seconds

    async def evaluate(
        self, candidate: Any, context: Mapping[str, Any] | None = None
    ) -> EvaluationResult:
        if not isinstance(candidate, BaseModel):
            raise TypeError("GenerationEvaluator requires a validated Pydantic model")
        context = context or {}
        key = fingerprint(
            {
                "candidate": candidate.model_dump(mode="json"),
                "context": dict(context),
                "threshold": self._threshold,
                "version": self.evaluator_version,
            }
        )
        cached = await self._cache.get("evaluation", key)
        if isinstance(cached, dict):
            return _result_from_mapping(cached)

        baseline = self._deterministic(candidate, context)
        result = await self._model_evaluation(candidate, context, baseline) or baseline
        await self._cache.set(
            "evaluation",
            key,
            {
                "overall_score": result.overall_score,
                "dimension_scores": dict(result.dimension_scores),
                "reasons": list(result.reasons),
                "recommendations": list(result.recommendations),
                "passed": result.passed,
                "evaluator_version": result.evaluator_version,
            },
            self._cache_ttl_seconds,
        )
        return result

    def _deterministic(
        self, candidate: BaseModel, context: Mapping[str, Any]
    ) -> EvaluationResult:
        scores = dict.fromkeys(_DIMENSIONS, 0.85)
        reasons: list[str] = ["The candidate passed strict schema validation."]
        recommendations: list[str] = []
        if isinstance(candidate, GeneratedRoadmap):
            scores["completeness"] = min(1.0, 0.65 + len(candidate.skills) * 0.05)
            scores["coverage"] = min(1.0, 0.7 + sum(len(s.tasks) for s in candidate.skills) * 0.01)
            scores["logical_flow"] = 1.0
            scores["progression"] = 0.9
            scores["estimated_hours"] = 1.0
            scores["task_consistency"] = 1.0
            scores["duplicate_skills"] = 1.0
            scores["duplicate_tasks"] = 1.0
        elif isinstance(candidate, GeneratedProject):
            scores["coverage"] = min(1.0, 0.65 + len(candidate.skills) * 0.08)
            scores["completeness"] = min(
                1.0,
                0.6
                + (len(candidate.requirements) + len(candidate.deliverables)) * 0.03,
            )
            scores["duplicate_skills"] = 1.0
            scores["task_consistency"] = 0.9
        if context:
            scores["personalization"] = 0.9
        else:
            scores["personalization"] = 0.7
            recommendations.append("Provide learner context to strengthen personalization.")
        overall = sum(scores.values()) / len(scores)
        return EvaluationResult(
            overall_score=overall,
            dimension_scores=scores,
            reasons=tuple(reasons),
            recommendations=tuple(recommendations),
            passed=overall >= self._threshold,
            evaluator_version=self.evaluator_version,
        )

    async def _model_evaluation(
        self,
        candidate: BaseModel,
        context: Mapping[str, Any],
        baseline: EvaluationResult,
    ) -> EvaluationResult | None:
        if self._provider is None or self._prompt_renderer is None:
            return None
        rendered = await self._prompt_renderer.render(
            "evaluation",
            {
                "generation_type": candidate.__class__.__name__,
                "original_request": dict(context),
                "candidate": candidate.model_dump(mode="json"),
                "deterministic_findings": list(baseline.reasons),
                "rubric": list(_DIMENSIONS),
            },
        )
        response = await self._provider.generate(
            GenerationRequest(
                prompt=rendered.text,
                response_schema=EvaluationOutput.model_json_schema(),
                prompt_id=rendered.prompt_id,
                prompt_version=rendered.version,
                temperature=0.0,
            )
        )
        try:
            output = EvaluationOutput.model_validate(json.loads(response.text))
        except (json.JSONDecodeError, ValidationError):
            return None
        scores = {
            dimension: float(output.dimension_scores.get(dimension, 0.0))
            for dimension in _DIMENSIONS
        }
        overall = sum(scores.values()) / len(scores)
        return EvaluationResult(
            overall_score=overall,
            dimension_scores=scores,
            reasons=tuple(output.reasons),
            recommendations=tuple(output.recommendations),
            passed=overall >= self._threshold and output.passed,
            evaluator_version=self.evaluator_version,
        )


def _result_from_mapping(value: Mapping[str, Any]) -> EvaluationResult:
    return EvaluationResult(
        overall_score=float(value["overall_score"]),
        dimension_scores={str(k): float(v) for k, v in value["dimension_scores"].items()},
        reasons=tuple(str(item) for item in value["reasons"]),
        recommendations=tuple(str(item) for item in value["recommendations"]),
        passed=bool(value["passed"]),
        evaluator_version=str(value["evaluator_version"]),
    )
