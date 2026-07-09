"""Idempotent document-to-vector indexing pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.core.interfaces.ai import (
    EmbeddingInput,
    EmbeddingProvider,
    EmbeddingPurpose,
    EmbeddingRequest,
)
from app.core.interfaces.vector_store import VectorRecord, VectorStore
from app.rag.chunker import SemanticChunker
from app.rag.documents import RAGChunk, RAGDocument
from app.utils.hashing import sha256_text


@dataclass(frozen=True, slots=True)
class IndexingResult:
    """Verified summary of one indexing operation."""

    document_count: int
    chunk_count: int
    cached_embedding_count: int


class RAGIndexer:
    """Chunk, embed, and idempotently upsert semantic documents."""

    def __init__(
        self,
        chunker: SemanticChunker,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self._chunker = chunker
        self._embeddings = embedding_provider
        self._vectors = vector_store

    async def index(
        self,
        documents: Sequence[RAGDocument],
        *,
        request_id: str | None = None,
        roadmap_id: str | None = None,
    ) -> IndexingResult:
        chunks = tuple(chunk for document in documents for chunk in self._chunker.chunk(document))
        if not chunks:
            return IndexingResult(len(documents), 0, 0)
        embedding_result = await self._embeddings.embed(
            EmbeddingRequest(
                items=tuple(
                    EmbeddingInput(chunk.content, metadata=chunk.metadata) for chunk in chunks
                ),
                purpose=EmbeddingPurpose.DOCUMENT,
                request_id=request_id,
                roadmap_id=roadmap_id,
            )
        )
        records = tuple(
            self._record(chunk, item.vector)
            for chunk, item in zip(chunks, embedding_result.items, strict=True)
        )
        await self._vectors.upsert(records)
        return IndexingResult(
            document_count=len(documents),
            chunk_count=len(chunks),
            cached_embedding_count=sum(item.cached for item in embedding_result.items),
        )

    @staticmethod
    def _record(chunk: RAGChunk, vector: Sequence[float]) -> VectorRecord:
        metadata = {
            **chunk.metadata,
            "content_hash": sha256_text(chunk.content),
            "source": chunk.source,
        }
        return VectorRecord(
            id=str(chunk.id),
            content=chunk.content,
            embedding=vector,
            metadata=metadata,
        )

