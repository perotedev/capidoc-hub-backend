from datetime import datetime, timezone
from uuid import UUID

from redis.asyncio import Redis

from app.modules.auth.domain.entities import UserSession

_SESSION_KEY_PREFIX = "session"
_USER_SESSIONS_SET_PREFIX = "user_sessions"


class RedisSessionRepository:
    """Redis-backed implementation of `SessionRepository`.

    Each session is a hash at `session:{user_id}:{session_id}` with a TTL equal to
    the refresh token's lifetime. A companion set `user_sessions:{user_id}` tracks
    every session_id for that user, enabling "list my sessions" / "logout everywhere".
    """

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def _session_key(self, user_id: UUID, session_id: str) -> str:
        return f"{_SESSION_KEY_PREFIX}:{user_id}:{session_id}"

    def _user_sessions_key(self, user_id: UUID) -> str:
        return f"{_USER_SESSIONS_SET_PREFIX}:{user_id}"

    async def create_session(self, session: UserSession) -> None:
        ttl_seconds = int((session.expires_at - datetime.now(timezone.utc)).total_seconds())
        if ttl_seconds <= 0:
            return

        session_key = self._session_key(session.user_id, session.session_id)
        await self._redis.hset(
            session_key,
            mapping={
                "user_agent": session.user_agent or "",
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
            },
        )
        await self._redis.expire(session_key, ttl_seconds)
        await self._redis.sadd(self._user_sessions_key(session.user_id), session.session_id)

    async def get_session(self, user_id: UUID, session_id: str) -> UserSession | None:
        data = await self._redis.hgetall(self._session_key(user_id, session_id))
        if not data:
            return None
        return UserSession(
            user_id=user_id,
            session_id=session_id,
            user_agent=data.get("user_agent") or None,
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )

    async def delete_session(self, user_id: UUID, session_id: str) -> None:
        await self._redis.delete(self._session_key(user_id, session_id))
        await self._redis.srem(self._user_sessions_key(user_id), session_id)

    async def delete_all_sessions(self, user_id: UUID) -> None:
        session_ids = await self._redis.smembers(self._user_sessions_key(user_id))
        for session_id in session_ids:
            await self._redis.delete(self._session_key(user_id, session_id))
        await self._redis.delete(self._user_sessions_key(user_id))

    async def list_sessions(self, user_id: UUID) -> list[UserSession]:
        session_ids = await self._redis.smembers(self._user_sessions_key(user_id))
        sessions: list[UserSession] = []
        stale_ids: list[str] = []
        for session_id in session_ids:
            session = await self.get_session(user_id, session_id)
            if session is None:
                stale_ids.append(session_id)
            else:
                sessions.append(session)
        if stale_ids:
            await self._redis.srem(self._user_sessions_key(user_id), *stale_ids)
        return sessions
