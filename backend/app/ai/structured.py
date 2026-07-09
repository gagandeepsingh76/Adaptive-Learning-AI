"""Typed structured generation with repair, retry, evaluation, and caching."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, TypeVar

from pydantic import BaseModel

from app.ai.repair import PromptRepairEngine
from app.ai.validation import ResponseValidator
from app.core.interfaces.ai import GenerationRequest, LLMProvider, QualityEvaluator
from app.core.interfaces.cache import AICache
from app.core.interfaces.observability import (
    AICallMetric,
    AIObservabilitySink,
    NullAIObservabilitySink,
)
from app.exceptions import AIQualityError, AIResponseValidationError, LLMStructuredOutputError
from app.utils.hashing import fingerprint
from app.utils.time import utc_now

OutputT = TypeVar("OutputT", bound=BaseModel)


class StructuredGenerationEngine:
    """Ensure callers receive validated typed objects and never raw model text."""

    def __init__(
        self,
        provider: LLMProvider,
        repair_engine: PromptRepairEngine,
        evaluator: QualityEvaluator,
        cache: AICache,
        observability: AIObservabilitySink | None = None,
        cache_ttl_seconds: int = 86_400,
    ) -> None:
        self._provider = provider
        self._repair = repair_engine
        self._evaluator = evaluator
        self._cache = cache
        self._sink = observability or NullAIObservabilitySink()
        self._cache_ttl_seconds = cache_ttl_seconds

    async def generate(
        self,
        request: GenerationRequest,
        schema: type[OutputT],
        *,
        quality_context: Mapping[str, Any] | None = None,
        validate_quality: bool = True,
    ) -> OutputT:
        """Generate, structurally validate, repair, evaluate, and cache one object."""
        request = replace(request, response_schema=schema.model_json_schema())
        validator = ResponseValidator(schema)
        cache_key = fingerprint(
            {
                "prompt": request.prompt,
                "prompt_id": request.prompt_id,
                "prompt_version": request.prompt_version,
                "model": request.model,
                "schema": schema.model_json_schema(),
            }
        )
        cached = await self._cache.get("structured_generation", cache_key)
        if isinstance(cached, dict):
            candidate = validator.validate_json(schema.model_validate(cached).model_dump_json())
            if not validate_quality:
                return candidate
            cached_evaluation = await self._evaluator.evaluate(candidate, quality_context)
            if cached_evaluation.passed:
                return candidate

        repair_attempts = 0
        validation_issues: list[str] = []
        response = await self._provider.generate(request)
        try:
            candidate = validator.validate_json(response.text)
        except AIResponseValidationError as exc:
            repair_attempts = 1
            validation_issues = _issues(exc)
            try:
                repaired = await self._repair.repair_json(
                    response.text, validation_issues, schema, request
                )
                candidate = validator.validate_json(repaired.text)
            except AIResponseValidationError as repair_exc:
                validation_issues = _issues(repair_exc)
                improved = self._repair.improve_prompt(request, validation_issues, 2)
                retried = await self._provider.generate(improved.request)
                try:
                    candidate = validator.validate_json(retried.text)
                except AIResponseValidationError as final_exc:
                    raise LLMStructuredOutputError(
                        "AI response remained invalid after repair and regeneration.",
                        details={"errors": _issues(final_exc)},
                    ) from final_exc

        evaluation_score: float | None = None
        if validate_quality:
            evaluation = await self._evaluator.evaluate(candidate, quality_context)
            evaluation_score = evaluation.overall_score
            if not evaluation.passed:
                improved = self._repair.improve_prompt(
                    request, list(evaluation.recommendations) or list(evaluation.reasons), 3
                )
                regenerated = await self._provider.generate(improved.request)
                try:
                    candidate = validator.validate_json(regenerated.text)
                except AIResponseValidationError as exc:
                    raise LLMStructuredOutputError(
                        "Quality regeneration returned an invalid response.",
                        details={"errors": _issues(exc)},
                    ) from exc
                evaluation = await self._evaluator.evaluate(candidate, quality_context)
                evaluation_score = evaluation.overall_score
                if not evaluation.passed:
                    raise AIQualityError(
                        "Generated content did not meet the configured quality threshold.",
                        details={
                            "score": evaluation.overall_score,
                            "recommendations": list(evaluation.recommendations),
                        },
                    )

        await self._cache.set(
            "structured_generation",
            cache_key,
            candidate.model_dump(mode="json"),
            self._cache_ttl_seconds,
        )
        await self._sink.record(
            AICallMetric(
                occurred_at=utc_now(),
                operation="structured_generation",
                provider="platform",
                model=request.model or "provider-default",
                latency_ms=response.latency_ms,
                request_id=request.request_id,
                roadmap_id=request.roadmap_id,
                prompt_id=request.prompt_id,
                prompt_version=request.prompt_version,
                repair_attempts=repair_attempts,
                evaluation_score=evaluation_score,
            )
        )
        return candidate


def _issues(exc: AIResponseValidationError) -> list[str]:
    details = exc.details or {}
    errors = details.get("errors", [])
    return [str(error) for error in errors] or [exc.message]
