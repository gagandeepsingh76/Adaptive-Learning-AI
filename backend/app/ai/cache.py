"""Persistent SQLite cache for AI platform artifacts."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from time import time
from typing import Any

from app.core.interfaces.cache import AICache


class SQLiteAICache(AICache):
    """Small durable cache with transactional expiry and namespace invalidation."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_cache (
                    namespace TEXT NOT NULL,
                    cache_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (namespace, cache_key)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS ix_ai_cache_expiry ON ai_cache(expires_at)"
            )

    async def get(self, namespace: str, key: str) -> Any | None:
        async with self._lock:
            return await asyncio.to_thread(self._get_sync, namespace, key)

    def _get_sync(self, namespace: str, key: str) -> Any | None:
        now = time()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload, expires_at FROM ai_cache "
                "WHERE namespace = ? AND cache_key = ?",
                (namespace, key),
            ).fetchone()
            if row is None:
                return None
            if float(row[1]) <= now:
                connection.execute(
                    "DELETE FROM ai_cache WHERE namespace = ? AND cache_key = ?",
                    (namespace, key),
                )
                return None
            return json.loads(str(row[0]))

    async def set(self, namespace: str, key: str, value: Any, ttl_seconds: int) -> None:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        async with self._lock:
            await asyncio.to_thread(
                self._set_sync, namespace, key, payload, time() + ttl_seconds
            )

    def _set_sync(self, namespace: str, key: str, payload: str, expires_at: float) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_cache(namespace, cache_key, payload, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(namespace, cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    expires_at = excluded.expires_at,
                    created_at = excluded.created_at
                """,
                (namespace, key, payload, expires_at, time()),
            )

    async def delete_namespace(self, namespace: str) -> int:
        async with self._lock:
            return await asyncio.to_thread(self._delete_namespace_sync, namespace)

    def _delete_namespace_sync(self, namespace: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM ai_cache WHERE namespace = ?", (namespace,))
            return cursor.rowcount

    async def close(self) -> None:
        return None

