"""Retriever fusion, mandatory filters, and context budget tests."""

from collections.abc import Sequence

from app.ai.cache import SQLiteAICache
from app.core.interfaces.vector_store import Metadata, VectorMatch, VectorRecord, VectorStore
from app.rag.context import ContextBuilder
from app.rag.retriever import RetrievalRequest, Retriever
from tests.fixtures.fakes import FakeEmbeddingProvider


class RecordingVectorStore(VectorStore):
    def __init__(self) -> None:
        self.filters: list[Metadata] = []

    async def initialize(self) -> None:
        return None

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        del records

    async def search(
        self, embedding: Sequence[float], filters: Metadata, limit: int
    ) -> tuple[VectorMatch, ...]:
        del embedding, limit
        self.filters.append(filters)
        return (
            VectorMatch(
                "chunk-1",
                "Learn dependency injection before provider adapters.",
                {"entity_type": "task", "entity_id": "t1", "order_index": 0},
                0.92,
            ),
        )

    async def delete(self, filters: Metadata) -> int:
        del filters
        return 0

    async def count(self) -> int:
        return 1

    async def close(self) -> None:
        return None


async def test_retriever_scopes_search_and_context_preserves_citation(
    ai_cache: SQLiteAICache,
) -> None:
    vector_store = RecordingVectorStore()
    retriever = Retriever(FakeEmbeddingProvider(), vector_store, ai_cache)

    result = await retriever.retrieve(
        RetrievalRequest("How should I structure providers?", "learner", "roadmap", 3)
    )
    context = ContextBuilder(max_tokens=200).build(result)

    assert result.chunks[0].id == "chunk-1"
    assert all(filters["learner_id"] == "learner" for filters in vector_store.filters)
    assert all(filters["content_version"] == 3 for filters in vector_store.filters)
    assert 'source_id="source:chunk-1"' in context.text
    assert context.sources[0].entity_id == "t1"
