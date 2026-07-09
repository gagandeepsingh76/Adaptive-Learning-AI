"""Persistent ChromaDB implementation of the vector-store contract."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings

from app.core.interfaces.vector_store import Metadata, VectorMatch, VectorRecord, VectorStore
from app.exceptions import VectorStoreError


class ChromaCollectionManager:
    """Own collection naming, initialization, and vector-space validation."""

    def __init__(self, path: Path, collection_name: str, dimensions: int) -> None:
        self._path = path
        self._name = collection_name
        self._dimensions = dimensions
        self._client: Any | None = None
        self._collection: Collection | None = None

    async def initialize(self) -> Collection:
        self._path.mkdir(parents=True, exist_ok=True)
        return await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> Collection:
        self._client = chromadb.PersistentClient(
            path=str(self._path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = self._client.get_or_create_collection(
            name=self._name,
            metadata={"hnsw:space": "cosine", "embedding_dimensions": self._dimensions},
        )
        existing_dimensions = collection.metadata.get("embedding_dimensions")
        if existing_dimensions != self._dimensions:
            raise VectorStoreError(
                "Chroma collection dimensions do not match configuration.",
                details={"expected": self._dimensions, "actual": existing_dimensions},
            )
        self._collection = collection
        return collection

    async def collection(self) -> Collection:
        if self._collection is None:
            return await self.initialize()
        return self._collection

    async def close(self) -> None:
        self._collection = None
        self._client = None


class ChromaVectorStore(VectorStore):
    """Async facade over Chroma's synchronous persistent client."""

    def __init__(self, manager: ChromaCollectionManager, dimensions: int) -> None:
        self._manager = manager
        self._dimensions = dimensions

    async def initialize(self) -> None:
        await self._manager.initialize()

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        if not records:
            return
        for record in records:
            if len(record.embedding) != self._dimensions:
                raise VectorStoreError(
                    "Vector dimension mismatch.",
                    details={"record_id": record.id, "expected": self._dimensions},
                )
        collection = await self._manager.collection()
        try:
            await asyncio.to_thread(
                cast(Any, collection.upsert),
                ids=[record.id for record in records],
                embeddings=[list(record.embedding) for record in records],
                metadatas=[dict(record.metadata) for record in records],
                documents=[record.content for record in records],
            )
        except Exception as exc:
            raise VectorStoreError(
                "Vector upsert failed.", details={"error_type": type(exc).__name__}
            ) from exc

    async def search(
        self, embedding: Sequence[float], filters: Metadata, limit: int
    ) -> tuple[VectorMatch, ...]:
        if len(embedding) != self._dimensions:
            raise VectorStoreError("Query vector dimension mismatch.")
        if limit < 1:
            raise ValueError("Search limit must be positive")
        collection = await self._manager.collection()
        try:
            result = await asyncio.to_thread(
                cast(Any, collection.query),
                query_embeddings=[list(embedding)],
                n_results=limit,
                where=_where(filters),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(
                "Vector similarity search failed.",
                details={"error_type": type(exc).__name__},
            ) from exc
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return tuple(
            VectorMatch(
                id=str(record_id),
                content=str(document or ""),
                metadata=cast(Metadata, dict(metadata or {})),
                relevance=max(0.0, min(1.0, 1.0 - float(distance))),
            )
            for record_id, document, metadata, distance in zip(
                ids, documents, metadatas, distances, strict=True
            )
        )

    async def delete(self, filters: Metadata) -> int:
        if not filters:
            raise ValueError("Refusing an unfiltered vector deletion")
        collection = await self._manager.collection()
        where = _where(filters)
        try:
            existing = await asyncio.to_thread(collection.get, where=where, include=[])
            ids = list(existing.get("ids") or [])
            if ids:
                await asyncio.to_thread(collection.delete, ids=ids)
            return len(ids)
        except Exception as exc:
            raise VectorStoreError(
                "Vector deletion failed.", details={"error_type": type(exc).__name__}
            ) from exc

    async def count(self) -> int:
        collection = await self._manager.collection()
        return int(await asyncio.to_thread(collection.count))

    async def close(self) -> None:
        await self._manager.close()


def _where(filters: Mapping[str, str | int | float | bool]) -> dict[str, Any] | None:
    if not filters:
        return None
    expressions = [{key: {"$eq": value}} for key, value in sorted(filters.items())]
    return expressions[0] if len(expressions) == 1 else {"$and": expressions}
