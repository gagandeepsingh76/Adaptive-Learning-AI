"""Query preprocessing, expansion, retrieval fusion, and ranking."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.core.interfaces.ai import (
    EmbeddingInput,
    EmbeddingProvider,
    EmbeddingPurpose,
    EmbeddingRequest,
)
from app.core.interfaces.cache import AICache
from app.core.interfaces.vector_store import Metadata, VectorMatch, VectorStore
from app.utils.hashing import fingerprint


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """Mandatory retrieval scope and search policy."""

    question: str
    learner_id: str
    roadmap_id: str
    content_version: int
    candidates_per_query: int = 20
    top_k: int = 8
    minimum_relevance: float = 0.25
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Ranked chunk with stable citation and score."""

    id: str
    content: str
    metadata: Metadata
    relevance: float
    citation: str


@dataclass(frozen=True, slots=True)
class RetrievedContext:
    """Structured retrieval result consumed by context builders."""

    canonical_question: str
    queries: tuple[str, ...]
    chunks: tuple[RetrievedChunk, ...]


class QueryPreprocessor:
    """Normalize question text without deleting user intent."""

    def normalize(self, question: str) -> str:
        value = unicodedata.normalize("NFKC", question)
        value = " ".join(value.split())
        if not 2 <= len(value) <= 4000:
            raise ValueError("Question length must be between 2 and 4000 characters")
        if any(unicodedata.category(char) == "Cc" for char in value):
            raise ValueError("Question contains unsupported control characters")
        return value


class QueryExpander:
    """Deterministic low-latency expansion for technical learning questions."""

    _PREFIXES = ("concepts and prerequisites", "practical tasks and completion criteria")

    def expand(self, question: str) -> tuple[str, ...]:
        queries = [question]
        words = re.findall(r"[A-Za-z0-9+#.-]+", question)
        if len(words) <= 12:
            for prefix in self._PREFIXES:
                queries.append(f"{prefix}: {question}")
        return tuple(dict.fromkeys(queries[:3]))


class Retriever:
    """Embed expanded queries, search with mandatory scope, and fuse rankings."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        cache: AICache,
        preprocessor: QueryPreprocessor | None = None,
        expander: QueryExpander | None = None,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self._embeddings = embedding_provider
        self._vectors = vector_store
        self._cache = cache
        self._preprocessor = preprocessor or QueryPreprocessor()
        self._expander = expander or QueryExpander()
        self._cache_ttl_seconds = cache_ttl_seconds

    async def retrieve(self, request: RetrievalRequest) -> RetrievedContext:
        canonical = self._preprocessor.normalize(request.question)
        queries = self._expander.expand(canonical)
        filters: dict[str, str | int | float | bool] = {
            "learner_id": request.learner_id,
            "roadmap_id": request.roadmap_id,
            "content_version": request.content_version,
        }
        cache_key = fingerprint(
            {
                "queries": queries,
                "filters": filters,
                "candidates": request.candidates_per_query,
                "top_k": request.top_k,
                "min": request.minimum_relevance,
            }
        )
        cached = await self._cache.get("similarity", cache_key)
        if isinstance(cached, list):
            return RetrievedContext(
                canonical_question=canonical,
                queries=queries,
                chunks=tuple(_chunk_from_mapping(item) for item in cached),
            )
        embedding_result = await self._embeddings.embed(
            EmbeddingRequest(
                items=tuple(EmbeddingInput(query) for query in queries),
                purpose=EmbeddingPurpose.QUERY,
                request_id=request.request_id,
                roadmap_id=request.roadmap_id,
            )
        )
        result_sets = await _search_all(
            self._vectors,
            [item.vector for item in embedding_result.items],
            filters,
            request.candidates_per_query,
        )
        chunks = _fuse(result_sets, request.minimum_relevance, request.top_k)
        await self._cache.set(
            "similarity",
            cache_key,
            [
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "metadata": dict(chunk.metadata),
                    "relevance": chunk.relevance,
                    "citation": chunk.citation,
                }
                for chunk in chunks
            ],
            self._cache_ttl_seconds,
        )
        return RetrievedContext(canonical, queries, chunks)


async def _search_all(
    store: VectorStore,
    vectors: Sequence[Sequence[float]],
    filters: Metadata,
    limit: int,
) -> list[tuple[VectorMatch, ...]]:
    import asyncio

    return list(
        await asyncio.gather(*(store.search(vector, filters, limit) for vector in vectors))
    )


def _fuse(
    result_sets: Sequence[Sequence[VectorMatch]], minimum: float, top_k: int
) -> tuple[RetrievedChunk, ...]:
    scores: dict[str, float] = {}
    records: dict[str, VectorMatch] = {}
    for result_set in result_sets:
        for rank, match in enumerate(result_set, start=1):
            if match.relevance < minimum:
                continue
            scores[match.id] = scores.get(match.id, 0.0) + 1.0 / (60 + rank)
            current = records.get(match.id)
            if current is None or match.relevance > current.relevance:
                records[match.id] = match
    ranked = sorted(
        records.values(),
        key=lambda match: (0.7 * match.relevance + 0.3 * scores[match.id]),
        reverse=True,
    )[:top_k]
    return tuple(
        RetrievedChunk(
            id=match.id,
            content=match.content,
            metadata=match.metadata,
            relevance=match.relevance,
            citation=f"source:{match.id}",
        )
        for match in ranked
    )


def _chunk_from_mapping(value: Any) -> RetrievedChunk:
    if not isinstance(value, dict):
        raise ValueError("Cached similarity result is invalid")
    return RetrievedChunk(
        id=str(value["id"]),
        content=str(value["content"]),
        metadata=dict(value["metadata"]),
        relevance=float(value["relevance"]),
        citation=str(value["citation"]),
    )

