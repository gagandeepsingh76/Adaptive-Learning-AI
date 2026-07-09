"""Persistent AI cache tests."""

from app.ai.cache import SQLiteAICache


async def test_cache_round_trip_and_namespace_invalidation(ai_cache: SQLiteAICache) -> None:
    await ai_cache.set("generation", "key", {"answer": 42}, 60)

    assert await ai_cache.get("generation", "key") == {"answer": 42}
    assert await ai_cache.delete_namespace("generation") == 1
    assert await ai_cache.get("generation", "key") is None

