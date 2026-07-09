"""Provider-neutral AI platform contracts and value objects."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EmbeddingPurpose(StrEnum):
    """Semantic role used to instruct embedding models."""

    DOCUMENT = "document"
    QUERY = "query"
    SIMILARITY = "similarity"


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Provider-reported token accounting."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Complete provider-neutral generation command."""

    prompt: str
    system_instruction: str | None = None
    response_schema: Mapping[str, Any] | None = None
    model: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_output_tokens: int | None = None
    prompt_id: str | None = None
    prompt_version: str | None = None
    request_id: str | None = None
    roadmap_id: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Provider result used internally by the structured-output engine."""

    text: str
    model: str
    usage: TokenUsage
    latency_ms: float
    retry_count: int
    finish_reason: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationChunk:
    """One provider-neutral streaming fragment."""

    text: str
    finish_reason: str | None = None
    usage: TokenUsage | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingInput:
    """One text and caller metadata in a batch request."""

    text: str
    metadata: Mapping[str, str | int | float | bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    """Batch embedding command."""

    items: Sequence[EmbeddingInput]
    purpose: EmbeddingPurpose
    model: str | None = None
    dimensions: int | None = None
    request_id: str | None = None
    roadmap_id: str | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingItem:
    """Validated vector paired with original metadata."""

    vector: tuple[float, ...]
    metadata: Mapping[str, str | int | float | bool]
    cached: bool


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    """Ordered embedding batch result."""

    items: tuple[EmbeddingItem, ...]
    model: str
    dimensions: int
    latency_ms: float
    retry_count: int


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    """Auditable rendered prompt and version lineage."""

    prompt_id: str
    version: str
    text: str
    prompt_hash: str
    variables_hash: str


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Normalized generation quality assessment."""

    overall_score: float
    dimension_scores: Mapping[str, float]
    reasons: tuple[str, ...]
    recommendations: tuple[str, ...]
    passed: bool
    evaluator_version: str


class LLMProvider(ABC):
    """Generation port replaceable by Gemini, OpenAI, Claude, or local models."""

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate one complete response."""

    @abstractmethod
    def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        """Stream a response without exposing provider SDK types."""


class EmbeddingProvider(ABC):
    """Batch dense-embedding port."""

    @abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed all inputs while preserving order and metadata."""


class PromptRenderer(ABC):
    """Versioned external prompt rendering port."""

    @abstractmethod
    async def render(
        self, prompt_id: str, variables: Mapping[str, Any], version: str | None = None
    ) -> RenderedPrompt:
        """Render and fingerprint a validated prompt asset."""


class QualityEvaluator(ABC):
    """Typed generation-quality evaluation port."""

    @abstractmethod
    async def evaluate(
        self, candidate: Any, context: Mapping[str, Any] | None = None
    ) -> EvaluationResult:
        """Score a validated candidate against the quality rubric."""
