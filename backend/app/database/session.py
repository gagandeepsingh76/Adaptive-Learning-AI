"""FastAPI database-session dependency."""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlmodel.ext.asyncio.session import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide one request-scoped session from the application database."""
    async for session in request.app.state.database.session():
        yield session

