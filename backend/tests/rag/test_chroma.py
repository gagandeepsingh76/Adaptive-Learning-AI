"""Chroma vector-store contract tests."""

from pathlib import Path

from app.core.interfaces.vector_store import VectorRecord
from app.rag.chroma import ChromaCollectionManager, ChromaVectorStore


async def test_chroma_upsert_filter_search_and_delete(tmp_path: Path) -> None:
    manager = ChromaCollectionManager(tmp_path / "chroma", "test-learning-content", 3)
    store = ChromaVectorStore(manager, 3)
    await store.initialize()
    await store.upsert(
        (
            VectorRecord(
                "one",
                "FastAPI routes",
                (1.0, 0.0, 0.0),
                {"learner_id": "a", "roadmap_id": "r", "content_version": 1},
            ),
            VectorRecord(
                "two",
                "SQL indexes",
                (0.0, 1.0, 0.0),
                {"learner_id": "b", "roadmap_id": "r", "content_version": 1},
            ),
        )
    )

    matches = await store.search(
        (1.0, 0.0, 0.0),
        {"learner_id": "a", "roadmap_id": "r", "content_version": 1},
        5,
    )

    assert [match.id for match in matches] == ["one"]
    assert await store.delete({"learner_id": "a"}) == 1
    assert await store.count() == 1
    await store.close()

