from typing import Protocol
from uuid import UUID

from app.modules.auth.domain.entities import UserSession


class SessionRepository(Protocol):
    """Persistence contract for `UserSession`, backed by Redis in this project."""

    async def create_session(self, session: UserSession) -> None: ...

    async def get_session(self, user_id: UUID, session_id: str) -> UserSession | None: ...

    async def delete_session(self, user_id: UUID, session_id: str) -> None: ...

    async def delete_all_sessions(self, user_id: UUID) -> None: ...

    async def list_sessions(self, user_id: UUID) -> list[UserSession]: ...


class PasswordResetRepository(Protocol):
    """Stores one-time password-reset codes (6-digit, email-keyed), backed by
    Redis in this project."""

    async def is_on_cooldown(self, email: str) -> bool: ...

    async def create_code(self, email: str) -> str: ...

    async def verify_code(self, email: str, code: str) -> bool: ...

    async def consume_code(self, email: str, code: str) -> bool: ...
