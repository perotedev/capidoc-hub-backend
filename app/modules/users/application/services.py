import secrets
import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.core.email import EmailService
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.modules.users.application.schemas import UserCreateRequest, UserUpdateRequest
from app.modules.users.domain.entities import UserEntity, UserSummary
from app.modules.users.domain.repositories import UserRepository
from app.shared.enums import Role


class UserService:
    """Application service orchestrating user use-cases on top of `UserRepository`."""

    def __init__(self, repository: UserRepository, email_service: EmailService) -> None:
        self._repository = repository
        self._email_service = email_service

    async def get_user(self, user_id: UUID) -> UserEntity:
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def get_by_email(self, email: str) -> UserEntity | None:
        return await self._repository.get_by_email(email)

    async def get_user_summary(self, user_id: UUID) -> UserSummary:
        summary = await self._repository.get_summary_by_id(user_id)
        if summary is None:
            raise NotFoundError(f"User {user_id} not found")
        return summary

    async def list_users(self, project_ids: list[UUID] | None) -> list[UserEntity]:
        return await self._repository.list_by_project(project_ids)

    async def search_users(
        self, query: str | None, role: Role | None, project_ids: list[UUID] | None
    ) -> list[UserEntity]:
        return await self._repository.search(query, role, project_ids)

    async def search_users_summary(
        self, query: str | None, role: Role | None, project_ids: list[UUID] | None
    ) -> list[UserSummary]:
        return await self._repository.search_summary(query, role, project_ids)

    async def create_user(self, request: UserCreateRequest) -> UserEntity:
        existing = await self._repository.get_by_email(request.email)
        if existing is not None:
            raise ConflictError(f"A user with email {request.email} already exists")

        now = datetime.now(timezone.utc)
        user = UserEntity(
            id=uuid.uuid4(),
            name=request.name,
            email=request.email,
            # No password is ever registered at creation — the account has no
            # usable credential until the user sets one via the "forgot
            # password" OTP flow, so this hash is an unguessable placeholder
            # that will never be typed in by anyone.
            password_hash=hash_password(secrets.token_urlsafe(32)),
            cpf=request.cpf,
            phone=request.phone,
            role=request.role,
            project_id=request.project_id,
            department_id=request.department_id,
            avatar_url=None,
            active=True,
            first_access=True,
            created_at=now,
            updated_at=now,
        )
        created = await self._repository.create(user)
        await self._email_service.send_welcome_email(created.email, created.name)
        return created

    async def update_user(self, user_id: UUID, request: UserUpdateRequest) -> UserEntity:
        user = await self.get_user(user_id)

        if request.email is not None and request.email != user.email:
            existing = await self._repository.get_by_email(request.email)
            if existing is not None:
                raise ConflictError(f"A user with email {request.email} already exists")
            user.email = request.email

        if request.name is not None:
            user.name = request.name
        if request.cpf is not None:
            user.cpf = request.cpf
        if request.phone is not None:
            user.phone = request.phone
        if request.role is not None:
            user.role = request.role
        if request.project_id is not None:
            user.project_id = request.project_id
        if request.department_id is not None:
            user.department_id = request.department_id
        if request.avatar_url is not None:
            user.avatar_url = request.avatar_url
        if request.active is not None:
            user.active = request.active

        return await self._repository.update(user)

    async def change_password(self, user_id: UUID, new_password: str) -> None:
        user = await self.get_user(user_id)
        user.password_hash = hash_password(new_password)
        user.first_access = False
        await self._repository.update(user)

    async def delete_user(self, user_id: UUID) -> None:
        await self.get_user(user_id)
        await self._repository.delete(user_id)
