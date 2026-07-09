"""Hierarchy-preserving semantic chunking."""

from __future__ import annotations

import re
from uuid import NAMESPACE_URL, uuid5

from app.rag.documents import RAGChunk, RAGDocument

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class SemanticChunker:
    """Split only within an entity, preferring paragraphs and complete sentences."""

    version = "semantic-1.0.0"

    def __init__(self, target_tokens: int, max_tokens: int, overlap_tokens: int) -> None:
        if not 0 <= overlap_tokens < target_tokens <= max_tokens:
            raise ValueError("Chunk token limits are inconsistent")
        self._target = target_tokens
        self._maximum = max_tokens
        self._overlap = overlap_tokens

    def chunk(self, document: RAGDocument) -> tuple[RAGChunk, ...]:
        """Return deterministic chunks with inherited metadata and hierarchy."""
        segments = self._segments(document.content)
        bodies: list[str] = []
        current: list[str] = []
        for segment in segments:
            prospective = "\n".join([*current, segment])
            if current and _token_count(prospective) > self._target:
                bodies.append("\n".join(current))
                current = self._overlap_segments(current)
            if _token_count(segment) > self._maximum:
                for sentence_group in self._hard_split(segment):
                    if current:
                        bodies.append("\n".join(current))
                        current = []
                    bodies.append(sentence_group)
            else:
                current.append(segment)
        if current:
            bodies.append("\n".join(current))
        bodies = [body for body in bodies if body.strip()]
        count = len(bodies)
        chunks: list[RAGChunk] = []
        for index, body in enumerate(bodies):
            chunk_id = uuid5(
                NAMESPACE_URL,
                f"chunk:{document.id}:{self.version}:{index}:{body}",
            )
            metadata = {
                **document.metadata,
                "document_id": str(document.id),
                "chunk_index": index,
                "chunk_count": count,
                "chunker_version": self.version,
            }
            chunks.append(
                RAGChunk(
                    id=chunk_id,
                    document_id=document.id,
                    content=body,
                    metadata=metadata,
                    source=document.source,
                    entity_type=document.entity_type,
                    entity_id=document.entity_id,
                    parent_id=document.parent_id,
                    embedding_version=document.embedding_version,
                    prompt_version=document.prompt_version,
                    created_at=document.created_at,
                    chunk_index=index,
                    chunk_count=count,
                )
            )
        return tuple(chunks)

    @staticmethod
    def _segments(content: str) -> list[str]:
        paragraphs = [value.strip() for value in re.split(r"\n{2,}", content) if value.strip()]
        return paragraphs or [content.strip()]

    def _hard_split(self, segment: str) -> list[str]:
        sentences = [value.strip() for value in _SENTENCE_BOUNDARY.split(segment) if value.strip()]
        groups: list[str] = []
        current: list[str] = []
        for sentence in sentences:
            if current and _token_count(" ".join([*current, sentence])) > self._maximum:
                groups.append(" ".join(current))
                current = []
            if _token_count(sentence) > self._maximum:
                words = sentence.split()
                for start in range(0, len(words), self._maximum):
                    groups.append(" ".join(words[start : start + self._maximum]))
            else:
                current.append(sentence)
        if current:
            groups.append(" ".join(current))
        return groups

    def _overlap_segments(self, segments: list[str]) -> list[str]:
        overlap: list[str] = []
        tokens = 0
        for segment in reversed(segments):
            count = _token_count(segment)
            if tokens + count > self._overlap:
                break
            overlap.insert(0, segment)
            tokens += count
        return overlap


def _token_count(value: str) -> int:
    """Conservative provider-independent token estimate."""
    return len(_TOKEN_PATTERN.findall(value))
