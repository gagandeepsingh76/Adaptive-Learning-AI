"""Database startup verification."""

from app.config.logging import get_logger
from app.database.engine import Database

logger = get_logger(__name__)


async def verify_database(database: Database) -> None:
    """Fail application startup if the configured database cannot be reached."""
    await database.ping()
    logger.info("database.ready")

