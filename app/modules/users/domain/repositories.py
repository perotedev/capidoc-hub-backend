from typing import Protocol
from uuid import UUID

from app.modules.users.domain.entities import UserEntity
from app.shared.enums import Role


class UserRepository(Protocol):
    """Persistence contract for `UserEntity`, implemented by the infrastructure layer."""

    async def get_by_id(self, user_id: UUID) -> UserEntity | None: ...

    async def get_by_email(self, email: str) -> UserEntity | None: ...

    async def list_by_project(self, project_id: UUID | None) -> list[UserEntity]: ...

    async def search(
        self,
        query: str | None,
        role: Role | None,
        project_id: UUID | None,
    ) -> list[UserEntity]: ...

    async def create(self, user: UserEntity) -> UserEntity: ...

    async def update(self, user: UserEntity) -> UserEntity: ...

    async def delete(self, user_id: UUID) -> None: ...
