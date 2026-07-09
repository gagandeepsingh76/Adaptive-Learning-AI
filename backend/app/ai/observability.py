"""Durable JSON Lines AI metrics sink."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.interfaces.observability import AICallMetric, AIObservabilitySink


class JsonlAIObservabilitySink(AIObservabilitySink):
    """Append-only persistent telemetry without coupling the AI layer to SQLModel."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def record(self, metric: AICallMetric) -> None:
        line = json.dumps(metric.to_dict(), ensure_ascii=False, sort_keys=True) + "\n"
        async with self._lock:
            await asyncio.to_thread(self._append, line)

    def _append(self, line: str) -> None:
        with self._path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
            stream.flush()

    async def close(self) -> None:
        return None
