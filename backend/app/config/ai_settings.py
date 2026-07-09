"""Framework-independent AI runtime policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config.settings import Settings


@dataclass(frozen=True, slots=True)
class AISettings:
    """Immutable configuration consumed only by AI platform adapters."""

    llm_model: str
    embedding_model: str
    embedding_dimensions: int
    generation_timeout_seconds: float
    embedding_timeout_seconds: float
    max_attempts: int
    temperature: float
    top_p: float
    top_k: int
    max_output_tokens: int
    safety_threshold: str
    input_cost_per_million: float
    output_cost_per_million: float
    metrics_path: Path
    cache_path: Path
    embedding_concurrency: int
    document_instruction: str
    query_instruction: str
    quality_threshold: float

    @classmethod
    def from_settings(cls, settings: Settings) -> AISettings:
        """Project application settings into the provider-neutral AI policy."""
        return cls(
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            embedding_dimensions=settings.embedding_dimensions,
            generation_timeout_seconds=settings.llm_timeout_seconds,
            embedding_timeout_seconds=settings.embedding_timeout_seconds,
            max_attempts=settings.provider_max_attempts,
            temperature=settings.ai_temperature,
            top_p=settings.ai_top_p,
            top_k=settings.ai_top_k,
            max_output_tokens=settings.ai_max_output_tokens,
            safety_threshold=settings.ai_safety_threshold,
            input_cost_per_million=settings.ai_input_cost_per_million,
            output_cost_per_million=settings.ai_output_cost_per_million,
            metrics_path=settings.ai_metrics_path,
            cache_path=settings.ai_cache_path,
            embedding_concurrency=settings.embedding_concurrency,
            document_instruction=settings.embedding_document_instruction,
            query_instruction=settings.embedding_query_instruction,
            quality_threshold=settings.quality_threshold,
        )
