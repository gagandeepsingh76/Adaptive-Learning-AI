"""Gemini Embedding 2 provider with ordered batch concurrency and caching."""

from __future__ import annotations

import asyncio
import math
from time import perf_counter
from typing import Any

from google import genai
from google.genai import types
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from app.ai.gemini import _is_retryable_provider_error
from app.config.ai_settings import AISettings
from app.core.interfaces.ai import (
    EmbeddingItem,
    EmbeddingProvider,
    EmbeddingPurpose,
    EmbeddingRequest,
    EmbeddingResult,
)
from app.core.interfaces.cache import AICache
from app.core.interfaces.observability import (
    AICallMetric,
    AIObservabilitySink,
    NullAIObservabilitySink,
)
from app.exceptions import LLMProviderError
from app.utils.hashing import fingerprint
from app.utils.time import utc_now


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Text embedding adapter for Gemini Embedding 2.

    Gemini Embedding 2 aggregates multiple contents into one vector, so a logical batch is
    executed as bounded concurrent single-content calls while preserving input order.
    """

    def __init__(
        self,
        api_key: str,
        settings: AISettings,
        cache: AICache,
        observability: AIObservabilitySink | None = None,
        client: Any | None = None,
        cache_ttl_seconds: int = 2_592_000,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("A Gemini API key is required")
        self._settings = settings
        self._cache = cache
        self._sink = observability or NullAIObservabilitySink()
        self._client = client or genai.Client(api_key=api_key)
        self._cache_ttl_seconds = cache_ttl_seconds

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if not request.items:
            raise ValueError("Embedding batch cannot be empty")
        model = request.model or self._settings.embedding_model
        dimensions = request.dimensions or self._settings.embedding_dimensions
        semaphore = asyncio.Semaphore(self._settings.embedding_concurrency)
        started = perf_counter()

        async def embed_one(index: int) -> tuple[int, EmbeddingItem, int]:
            item = request.items[index]
            instructed = self._instruction(request.purpose, item.text)
            key = fingerprint(
                {
                    "model": model,
                    "dimensions": dimensions,
                    "purpose": request.purpose.value,
                    "content": instructed,
                }
            )
            namespace = f"embedding:{model}:d{dimensions}"
            cached = await self._cache.get(namespace, key)
            if isinstance(cached, list):
                vector = self._validate_vector(cached, dimensions)
                return index, EmbeddingItem(vector, item.metadata, True), 0

            async with semaphore:
                vector, retries = await self._embed_uncached(instructed, model, dimensions)
            await self._cache.set(namespace, key, list(vector), self._cache_ttl_seconds)
            return index, EmbeddingItem(vector, item.metadata, False), retries

        results = await asyncio.gather(*(embed_one(index) for index in range(len(request.items))))
        results.sort(key=lambda value: value[0])
        retry_count = sum(value[2] for value in results)
        latency_ms = (perf_counter() - started) * 1000
        await self._sink.record(
            AICallMetric(
                occurred_at=utc_now(),
                operation="embedding",
                provider="gemini",
                model=model,
                embedding_model=model,
                latency_ms=latency_ms,
                request_id=request.request_id,
                roadmap_id=request.roadmap_id,
                retry_count=retry_count,
            )
        )
        return EmbeddingResult(
            items=tuple(value[1] for value in results),
            model=model,
            dimensions=dimensions,
            latency_ms=latency_ms,
            retry_count=retry_count,
        )

    async def _embed_uncached(
        self, content: str, model: str, dimensions: int
    ) -> tuple[tuple[float, ...], int]:
        retries = 0
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._settings.max_attempts),
                wait=wait_exponential_jitter(initial=0.5, max=8),
                retry=retry_if_exception(_is_retryable_provider_error),
                reraise=True,
            ):
                retries = attempt.retry_state.attempt_number - 1
                with attempt:
                    async with asyncio.timeout(self._settings.embedding_timeout_seconds):
                        response = await self._client.aio.models.embed_content(
                            model=model,
                            contents=content,
                            config=types.EmbedContentConfig(
                                output_dimensionality=dimensions
                            ),
                        )
            embeddings = getattr(response, "embeddings", None) or []
            if len(embeddings) != 1:
                raise LLMProviderError("Gemini returned an invalid embedding count.")
            return self._validate_vector(embeddings[0].values, dimensions), retries
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(
                "Gemini embedding failed.", details={"error_type": type(exc).__name__}
            ) from exc

    def _instruction(self, purpose: EmbeddingPurpose, text: str) -> str:
        clean = " ".join(text.split())
        if purpose is EmbeddingPurpose.DOCUMENT:
            return f"{self._settings.document_instruction}\n{clean}"
        if purpose is EmbeddingPurpose.QUERY:
            return f"{self._settings.query_instruction}\n{clean}"
        return clean

    @staticmethod
    def _validate_vector(values: Any, dimensions: int) -> tuple[float, ...]:
        vector = tuple(float(value) for value in values)
        if len(vector) != dimensions:
            raise LLMProviderError(
                "Embedding dimension mismatch.",
                details={"expected": dimensions, "actual": len(vector)},
            )
        if not all(math.isfinite(value) for value in vector):
            raise LLMProviderError("Embedding contains a non-finite value.")
        return vector
