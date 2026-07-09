"""Durable AI telemetry contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class AICallMetric:
    """Low-cardinality audit record for one AI platform operation."""

    occurred_at: datetime
    operation: str
    provider: str
    model: str
    latency_ms: float
    request_id: str | None = None
    roadmap_id: str | None = None
    prompt_id: str | None = None
    prompt_version: str | None = None
    embedding_model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    retry_count: int = 0
    repair_attempts: int = 0
    evaluation_score: float | None = None
    outcome: str = "success"
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary without prompt or user content."""
        value = asdict(self)
        value["occurred_at"] = self.occurred_at.isoformat()
        return value


class AIObservabilitySink(ABC):
    """Persistence port for AI metrics and audit events."""

    @abstractmethod
    async def record(self, metric: AICallMetric) -> None:
        """Persist one metric without blocking the caller's event loop."""

    @abstractmethod
    async def close(self) -> None:
        """Flush and release sink resources."""


class NullAIObservabilitySink(AIObservabilitySink):
    """Explicit no-op sink for deterministic tests and local tools."""

    async def record(self, metric: AICallMetric) -> None:
        del metric

    async def close(self) -> None:
        return None

