from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.shared.enums import Role


@dataclass(slots=True)
class UserEntity:
    """Domain representation of a user, independent of how it is persisted."""

    id: UUID
    name: str
    email: str
    password_hash: str
    cpf: str | None
    phone: str | None
    role: Role
    project_id: UUID | None
    department_id: UUID | None
    avatar_url: str | None
    active: bool
    first_access: bool
    created_at: datetime
    updated_at: datetime

    def is_super_admin(self) -> bool:
        return self.role == Role.SUPER_ADMIN

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_auditor(self) -> bool:
        return self.role == Role.AUDITOR

    def can_authenticate(self) -> bool:
        return self.active


@dataclass(slots=True)
class UserSummary:
    """A user enriched with denormalized names for API responses."""

    user: UserEntity
    project_name: str | None
    department_name: str | None
