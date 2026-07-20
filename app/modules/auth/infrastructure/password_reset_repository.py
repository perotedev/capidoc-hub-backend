import secrets
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()

_TOKEN_KEY_PREFIX = "password_reset"


class RedisPasswordResetRepository:
    """Redis-backed implementation of `PasswordResetRepository`.

    Each token is a short-lived key `password_reset:{token}` -> user_id, so a
    stolen or expired token simply stops resolving to anyone.
    """

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def _token_key(self, token: str) -> str:
        return f"{_TOKEN_KEY_PREFIX}:{token}"

    async def create_token(self, user_id: UUID) -> str:
        token = secrets.token_urlsafe(32)
        await self._redis.set(
            self._token_key(token),
            str(user_id),
            ex=settings.password_reset_token_expire_minutes * 60,
        )
        return token

    async def get_user_id(self, token: str) -> UUID | None:
        raw_user_id = await self._redis.get(self._token_key(token))
        return UUID(raw_user_id) if raw_user_id else None

    async def delete_token(self, token: str) -> None:
        await self._redis.delete(self._token_key(token))
