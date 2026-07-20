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
    """Stores one-time password-reset tokens, backed by Redis in this project."""

    async def create_token(self, user_id: UUID) -> str: ...

    async def get_user_id(self, token: str) -> UUID | None: ...

    async def delete_token(self, token: str) -> None: ...
