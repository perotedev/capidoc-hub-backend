from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.redis_client import get_redis_client
from app.core.storage import StorageService, get_storage_service

settings = get_settings()

_FILE_URL_CACHE_PREFIX = "file_url"


class FileUrlCacheService:
    """Caches signed S3/MinIO file URLs in Redis so we don't re-sign on every request.

    The cache TTL mirrors the presigned URL's own expiry (24h by default), so a
    cached entry never outlives the URL it stores.
    """

    def __init__(self, redis_client: Redis, storage_service: StorageService) -> None:
        self._redis = redis_client
        self._storage = storage_service

    def _cache_key(self, file_key: str) -> str:
        return f"{_FILE_URL_CACHE_PREFIX}:{file_key}"

    async def get_signed_url(self, file_key: str) -> str:
        cache_key = self._cache_key(file_key)
        cached_url = await self._redis.get(cache_key)
        if cached_url:
            return cached_url

        signed_url = self._storage.generate_presigned_url(file_key, settings.file_url_expire_seconds)
        await self._redis.set(cache_key, signed_url, ex=settings.file_url_expire_seconds)
        return signed_url

    async def invalidate(self, file_key: str) -> None:
        await self._redis.delete(self._cache_key(file_key))


def get_file_url_cache_service(
    redis_client: Annotated[Redis, Depends(get_redis_client)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> FileUrlCacheService:
    return FileUrlCacheService(redis_client, storage_service)


FileUrlCacheServiceDep = Annotated[FileUrlCacheService, Depends(get_file_url_cache_service)]
