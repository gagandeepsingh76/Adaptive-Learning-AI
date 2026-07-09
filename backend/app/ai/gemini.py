"""Gemini implementation of the provider-neutral LLM contract."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from google import genai
from google.genai import types
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from app.config.ai_settings import AISettings
from app.config.logging import get_logger
from app.core.interfaces.ai import (
    GenerationChunk,
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    TokenUsage,
)
from app.core.interfaces.observability import (
    AICallMetric,
    AIObservabilitySink,
    NullAIObservabilitySink,
)
from app.exceptions import LLMProviderError
from app.utils.time import utc_now

logger = get_logger(__name__)


class GeminiProvider(LLMProvider):
    """Configurable Gemini generation adapter with bounded retries and telemetry."""

    def __init__(
        self,
        api_key: str,
        settings: AISettings,
        observability: AIObservabilitySink | None = None,
        client: Any | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("A Gemini API key is required")
        self._settings = settings
        self._sink = observability or NullAIObservabilitySink()
        self._client = client or genai.Client(api_key=api_key)

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate a complete response and normalize provider accounting."""
        model = request.model or self._settings.llm_model
        started = perf_counter()
        retry_count = 0
        try:
            async for attempt in self._retrying():
                retry_count = attempt.retry_state.attempt_number - 1
                with attempt:
                    async with asyncio.timeout(self._settings.generation_timeout_seconds):
                        response = await self._client.aio.models.generate_content(
                            model=model,
                            contents=request.prompt,
                            config=self._generation_config(request),
                        )
            result = self._to_result(response, model, started, retry_count)
            await self._record(request, result, "success", None)
            return result
        except Exception as exc:
            latency_ms = (perf_counter() - started) * 1000
            await self._record_failure(request, model, latency_ms, retry_count, exc)
            if isinstance(exc, LLMProviderError):
                raise
            raise LLMProviderError(
                "Gemini generation failed.", details={"error_type": type(exc).__name__}
            ) from exc

    async def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        """Stream normalized text chunks while retaining provider independence."""
        model = request.model or self._settings.llm_model
        started = perf_counter()
        usage = TokenUsage()
        try:
            async with asyncio.timeout(self._settings.generation_timeout_seconds):
                stream = await self._client.aio.models.generate_content_stream(
                    model=model,
                    contents=request.prompt,
                    config=self._generation_config(request),
                )
                async for response in stream:
                    text = self._extract_text(response, allow_empty=True)
                    usage = self._usage(response) or usage
                    finish_reason = self._finish_reason(response)
                    if text or finish_reason:
                        yield GenerationChunk(
                            text=text, finish_reason=finish_reason, usage=usage
                        )
            result = GenerationResult(
                text="",
                model=model,
                usage=usage,
                latency_ms=(perf_counter() - started) * 1000,
                retry_count=0,
            )
            await self._record(request, result, "success", None)
        except Exception as exc:
            await self._record_failure(
                request, model, (perf_counter() - started) * 1000, 0, exc
            )
            raise LLMProviderError(
                "Gemini streaming generation failed.",
                details={"error_type": type(exc).__name__},
            ) from exc

    def _generation_config(self, request: GenerationRequest) -> types.GenerateContentConfig:
        threshold = types.HarmBlockThreshold(self._settings.safety_threshold)
        categories = (
            types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        )
        return types.GenerateContentConfig(
            system_instruction=request.system_instruction,
            temperature=request.temperature
            if request.temperature is not None
            else self._settings.temperature,
            top_p=request.top_p if request.top_p is not None else self._settings.top_p,
            top_k=request.top_k if request.top_k is not None else self._settings.top_k,
            max_output_tokens=request.max_output_tokens
            if request.max_output_tokens is not None
            else self._settings.max_output_tokens,
            response_mime_type="application/json" if request.response_schema else "text/plain",
            response_json_schema=dict(request.response_schema) if request.response_schema else None,
            safety_settings=[
                types.SafetySetting(category=category, threshold=threshold)
                for category in categories
            ],
        )

    def _to_result(
        self, response: Any, model: str, started: float, retry_count: int
    ) -> GenerationResult:
        text = self._extract_text(response)
        return GenerationResult(
            text=text,
            model=model,
            usage=self._usage(response),
            latency_ms=(perf_counter() - started) * 1000,
            retry_count=retry_count,
            finish_reason=self._finish_reason(response),
        )

    @staticmethod
    def _extract_text(response: Any, *, allow_empty: bool = False) -> str:
        try:
            value = response.text
        except (AttributeError, ValueError) as exc:
            raise LLMProviderError("Gemini blocked or omitted response content.") from exc
        if not value and not allow_empty:
            raise LLMProviderError("Gemini returned an empty response.")
        return value or ""

    @staticmethod
    def _usage(response: Any) -> TokenUsage:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return TokenUsage()
        return TokenUsage(
            input_tokens=int(getattr(usage, "prompt_token_count", 0) or 0),
            output_tokens=int(getattr(usage, "candidates_token_count", 0) or 0),
            total_tokens=int(getattr(usage, "total_token_count", 0) or 0),
        )

    @staticmethod
    def _finish_reason(response: Any) -> str | None:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None
        reason = getattr(candidates[0], "finish_reason", None)
        return str(getattr(reason, "value", reason)) if reason is not None else None

    def _retrying(self) -> AsyncRetrying:
        return AsyncRetrying(
            stop=stop_after_attempt(self._settings.max_attempts),
            wait=wait_exponential_jitter(initial=0.5, max=8),
            retry=retry_if_exception(_is_retryable_provider_error),
            reraise=True,
        )

    async def _record(
        self,
        request: GenerationRequest,
        result: GenerationResult,
        outcome: str,
        error_code: str | None,
    ) -> None:
        cost = (
            result.usage.input_tokens * self._settings.input_cost_per_million
            + result.usage.output_tokens * self._settings.output_cost_per_million
        ) / 1_000_000
        await self._sink.record(
            AICallMetric(
                occurred_at=utc_now(),
                operation="generation",
                provider="gemini",
                model=result.model,
                latency_ms=result.latency_ms,
                request_id=request.request_id,
                roadmap_id=request.roadmap_id,
                prompt_id=request.prompt_id,
                prompt_version=request.prompt_version,
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                estimated_cost=cost,
                retry_count=result.retry_count,
                outcome=outcome,
                error_code=error_code,
            )
        )

    async def _record_failure(
        self,
        request: GenerationRequest,
        model: str,
        latency_ms: float,
        retry_count: int,
        exc: Exception,
    ) -> None:
        logger.warning(
            "ai.generation.failed",
            model=model,
            retry_count=retry_count,
            error_type=type(exc).__name__,
        )
        result = GenerationResult(
            text="", model=model, usage=TokenUsage(), latency_ms=latency_ms, retry_count=retry_count
        )
        await self._record(request, result, "failure", type(exc).__name__)


def _is_retryable_provider_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, asyncio.TimeoutError)):
        return True
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return status_code == 429 or (isinstance(status_code, int) and status_code >= 500)

