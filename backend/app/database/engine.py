"""Async SQLAlchemy engine and session lifecycle."""

from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.settings import Settings


class Database:
    """Own the async database engine and request-scoped session factory."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._ensure_sqlite_directory(settings.database_url)
        self.engine: AsyncEngine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        if settings.database_url.startswith("sqlite"):
            event.listen(self.engine.sync_engine, "connect", _configure_sqlite)

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield one session and guarantee closure after the request."""
        async with self.session_factory() as session:
            yield session

    async def ping(self) -> None:
        """Verify database connectivity with a bounded trivial query."""
        async with self.session_factory() as session:
            await session.exec(select(1))

    async def create_schema_for_tests(self) -> None:
        """Create metadata directly for isolated tests; production uses Alembic."""
        importlib.import_module("app.models")
        async with self.engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)

    async def drop_schema_for_tests(self) -> None:
        """Drop metadata directly for isolated tests."""
        async with self.engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.drop_all)

    async def dispose(self) -> None:
        """Release all pooled database resources."""
        await self.engine.dispose()

    @staticmethod
    def _ensure_sqlite_directory(database_url: str) -> None:
        if not database_url.startswith("sqlite") or ":memory:" in database_url:
            return
        path = database_url.rsplit("///", maxsplit=1)[-1]
        Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _configure_sqlite(dbapi_connection: Any, _connection_record: Any) -> None:
    """Enable integrity and concurrency pragmas on every SQLite connection."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def create_database(settings: Settings) -> Database:
    """Build a database resource from validated settings."""
    return Database(settings)
