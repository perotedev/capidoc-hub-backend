from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class UserSession:
    """A single logged-in session for a user, tracked in Redis via its refresh-token jti."""

    user_id: UUID
    session_id: str
    user_agent: str | None
    created_at: datetime
    expires_at: datetime
