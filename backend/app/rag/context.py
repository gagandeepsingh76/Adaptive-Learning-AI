"""Token-budgeted context construction with source attribution."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.rag.retriever import RetrievedChunk, RetrievedContext

_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@dataclass(frozen=True, slots=True)
class ContextSource:
    """Source descriptor safe to expose with an answer."""

    source_id: str
    entity_type: str
    entity_id: str
    relevance: float


@dataclass(frozen=True, slots=True)
class BuiltContext:
    """Bounded prompt context and ordered source map."""

    text: str
    sources: tuple[ContextSource, ...]
    estimated_tokens: int


class ContextBuilder:
    """Select only relevant chunks under a hard context token budget."""

    def __init__(self, max_tokens: int = 4000) -> None:
        if max_tokens < 100:
            raise ValueError("Context budget is too small")
        self._max_tokens = max_tokens

    def build(self, retrieved: RetrievedContext) -> BuiltContext:
        selected: list[tuple[RetrievedChunk, str, int]] = []
        used = 0
        for chunk in retrieved.chunks:
            formatted = self._format_chunk(chunk.citation, chunk.content)
            tokens = len(_TOKEN_PATTERN.findall(formatted))
            if used + tokens > self._max_tokens:
                continue
            selected.append((chunk, formatted, tokens))
            used += tokens
        ordered = sorted(
            selected,
            key=lambda item: (
                int(item[0].metadata.get("order_index", 0)),
                int(item[0].metadata.get("chunk_index", 0)),
            ),
        )
        text = "\n\n".join(item[1] for item in ordered)
        sources = tuple(
            ContextSource(
                source_id=item[0].citation,
                entity_type=str(item[0].metadata.get("entity_type", "unknown")),
                entity_id=str(item[0].metadata.get("entity_id", "unknown")),
                relevance=item[0].relevance,
            )
            for item in ordered
        )
        return BuiltContext(text=text, sources=sources, estimated_tokens=used)

    @staticmethod
    def _format_chunk(citation: str, content: str) -> str:
        return f"<retrieved_chunk source_id=\"{citation}\">\n{content}\n</retrieved_chunk>"
