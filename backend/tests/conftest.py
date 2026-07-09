"""Shared AI platform fixtures."""

from pathlib import Path

import pytest

from app.ai.cache import SQLiteAICache
from app.config.ai_settings import AISettings


@pytest.fixture
def ai_settings(tmp_path: Path) -> AISettings:
    return AISettings(
        llm_model="openai/gpt-4.1-mini",
        embedding_model="openai/text-embedding-3-small",
        embedding_dimensions=3,
        generation_timeout_seconds=5,
        embedding_timeout_seconds=5,
        max_attempts=2,
        temperature=0.2,
        top_p=0.9,
        top_k=40,
        max_output_tokens=1024,
        safety_threshold="BLOCK_MEDIUM_AND_ABOVE",
        input_cost_per_million=1.0,
        output_cost_per_million=2.0,
        metrics_path=tmp_path / "metrics.jsonl",
        cache_path=tmp_path / "cache.sqlite3",
        embedding_concurrency=2,
        document_instruction="Document:",
        query_instruction="Query:",
        quality_threshold=0.8,
    )


@pytest.fixture
def ai_cache(tmp_path: Path) -> SQLiteAICache:
    return SQLiteAICache(tmp_path / "ai-cache.sqlite3")
