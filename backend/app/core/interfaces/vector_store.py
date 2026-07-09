"""Provider-neutral vector storage contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

type MetadataValue = str | int | float | bool
type Metadata = Mapping[str, MetadataValue]


@dataclass(frozen=True, slots=True)
class VectorRecord:
    """One vectorized chunk ready for upsert."""

    id: str
    content: str
    embedding: Sequence[float]
    metadata: Metadata


@dataclass(frozen=True, slots=True)
class VectorMatch:
    """Normalized higher-is-better similarity result."""

    id: str
    content: str
    metadata: Metadata
    relevance: float


class VectorStore(ABC):
    """Dense vector store replaceable by Chroma, Pinecone, or Qdrant."""

    @abstractmethod
    async def initialize(self) -> None:
        """Create or validate the configured collection."""

    @abstractmethod
    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        """Idempotently insert or update vector records."""

    @abstractmethod
    async def search(
        self, embedding: Sequence[float], filters: Metadata, limit: int
    ) -> tuple[VectorMatch, ...]:
        """Return filtered results ordered by descending relevance."""

    @abstractmethod
    async def delete(self, filters: Metadata) -> int:
        """Delete matching records and return the prior match count."""

    @abstractmethod
    async def count(self) -> int:
        """Return collection record count."""

    @abstractmethod
    async def close(self) -> None:
        """Release client resources."""
