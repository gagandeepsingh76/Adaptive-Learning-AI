"""AI cache contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AICache(ABC):
    """Namespaced asynchronous cache for JSON-compatible AI artifacts."""

    @abstractmethod
    async def get(self, namespace: str, key: str) -> Any | None:
        """Return a non-expired value or `None`."""

    @abstractmethod
    async def set(self, namespace: str, key: str, value: Any, ttl_seconds: int) -> None:
        """Store a JSON-compatible value with a required expiry."""

    @abstractmethod
    async def delete_namespace(self, namespace: str) -> int:
        """Delete a namespace and return the number of removed entries."""

    @abstractmethod
    async def close(self) -> None:
        """Release persistent resources."""

