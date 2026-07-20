import secrets

from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()

_CODE_KEY_PREFIX = "password_reset_code"
_COOLDOWN_KEY_PREFIX = "password_reset_cooldown"


class RedisPasswordResetRepository:
    """Redis-backed implementation of `PasswordResetRepository`.

    Each pending code is a hash `password_reset_code:{email}` -> {code, attempts},
    expiring after `password_reset_code_expire_minutes`. A separate cooldown key
    enforces the one-request-per-minute rule regardless of whether the email
    belongs to a real account (so the rate-limit response can't be used to probe
    which emails are registered). A code is deleted as soon as it is consumed
    (successful reset) or once verification attempts are exhausted.
    """

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def _code_key(self, email: str) -> str:
        return f"{_CODE_KEY_PREFIX}:{email.strip().lower()}"

    def _cooldown_key(self, email: str) -> str:
        return f"{_COOLDOWN_KEY_PREFIX}:{email.strip().lower()}"

    async def is_on_cooldown(self, email: str) -> bool:
        return bool(await self._redis.exists(self._cooldown_key(email)))

    async def create_code(self, email: str) -> str:
        code = f"{secrets.randbelow(1_000_000):06d}"
        key = self._code_key(email)
        await self._redis.hset(key, mapping={"code": code, "attempts": 0})
        await self._redis.expire(key, settings.password_reset_code_expire_minutes * 60)
        await self._redis.set(self._cooldown_key(email), "1", ex=settings.password_reset_cooldown_seconds)
        return code

    async def verify_code(self, email: str, code: str) -> bool:
        return await self._check_code(email, code)

    async def consume_code(self, email: str, code: str) -> bool:
        valid = await self._check_code(email, code)
        if valid:
            await self._redis.delete(self._code_key(email))
        return valid

    async def _check_code(self, email: str, code: str) -> bool:
        key = self._code_key(email)
        data = await self._redis.hgetall(key)
        if not data:
            return False

        if int(data.get("attempts", 0)) >= settings.password_reset_max_attempts:
            await self._redis.delete(key)
            return False

        if data.get("code") != code:
            await self._redis.hincrby(key, "attempts", 1)
            return False

        return True
