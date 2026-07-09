"""Alembic migration environment."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context
from app import models  # noqa: F401
from app.config.settings import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _ensure_sqlite_directory(url: str) -> None:
    if not url.startswith("sqlite") or ":memory:" in url:
        return
    path = url.rsplit("///", maxsplit=1)[-1]
    Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


database_url = get_settings().database_url
_ensure_sqlite_directory(database_url)
config.set_main_option("sqlalchemy.url", database_url)
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating an Engine."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure and execute migrations on a synchronous bridge connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and bridge Alembic's synchronous migration API."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
