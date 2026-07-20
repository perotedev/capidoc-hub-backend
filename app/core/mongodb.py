from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import get_settings

settings = get_settings()

_mongo_client: AsyncMongoClient | None = None


def get_mongo_client() -> AsyncMongoClient:
    """Lazily creates a single shared async MongoDB client for the process."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncMongoClient(settings.mongo_dsn)
    return _mongo_client


def get_mongo_db() -> AsyncDatabase:
    """FastAPI dependency returning the application's MongoDB database handle."""
    return get_mongo_client()[settings.mongo_db]


async def close_mongo_client() -> None:
    global _mongo_client
    if _mongo_client is not None:
        await _mongo_client.close()
        _mongo_client = None
