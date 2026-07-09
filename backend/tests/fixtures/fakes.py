"""Deterministic AI platform test doubles."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import Any

from app.core.interfaces.ai import (
    EmbeddingItem,
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResult,
    EvaluationResult,
    GenerationChunk,
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    PromptRenderer,
    QualityEvaluator,
    RenderedPrompt,
    TokenUsage,
)
from app.utils.hashing import sha256_text


class FakeLLMProvider(LLMProvider):
    """Return queued strings while recording requests."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.requests: list[GenerationRequest] = []

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.requests.append(request)
        return GenerationResult(
            text=self.responses.pop(0),
            model=request.model or "fake-model",
            usage=TokenUsage(10, 20, 30),
            latency_ms=1.0,
            retry_count=0,
        )

    async def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        self.requests.append(request)
        yield GenerationChunk(text=self.responses.pop(0))


class FakePromptRenderer(PromptRenderer):
    async def render(
        self, prompt_id: str, variables: Mapping[str, Any], version: str | None = None
    ) -> RenderedPrompt:
        text = f"{prompt_id}:{variables}"
        return RenderedPrompt(prompt_id, version or "1.0.0", text, sha256_text(text), "vars")


class PassingEvaluator(QualityEvaluator):
    async def evaluate(
        self, candidate: Any, context: Mapping[str, Any] | None = None
    ) -> EvaluationResult:
        del candidate, context
        return EvaluationResult(0.95, {"quality": 0.95}, ("valid",), (), True, "test")


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, vector: tuple[float, ...] = (1.0, 0.0, 0.0)) -> None:
        self.vector = vector
        self.calls = 0

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.calls += 1
        return EmbeddingResult(
            items=tuple(EmbeddingItem(self.vector, item.metadata, False) for item in request.items),
            model="fake-embedding",
            dimensions=len(self.vector),
            latency_ms=1.0,
            retry_count=0,
        )

