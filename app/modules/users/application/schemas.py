from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.modules.users.domain.entities import UserSummary
from app.shared.enums import Role
from app.shared.schema import CamelCaseModel


class UserCreateRequest(CamelCaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    cpf: str | None = Field(default=None, max_length=14)
    phone: str | None = Field(default=None, max_length=20)
    role: Role
    project_id: UUID | None = None
    department_id: UUID | None = None


class UserUpdateRequest(CamelCaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    cpf: str | None = Field(default=None, max_length=14)
    phone: str | None = Field(default=None, max_length=20)
    role: Role | None = None
    project_id: UUID | None = None
    department_id: UUID | None = None
    avatar_url: str | None = None
    active: bool | None = None


class UserResponse(CamelCaseModel):
    id: UUID
    name: str
    email: str
    cpf: str | None
    phone: str | None
    role: Role
    project_id: UUID | None
    project_name: str | None = None
    department_id: UUID | None
    department_name: str | None = None
    avatar_url: str | None
    active: bool
    first_access: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_summary(cls, summary: UserSummary) -> "UserResponse":
        return cls(
            id=summary.user.id,
            name=summary.user.name,
            email=summary.user.email,
            cpf=summary.user.cpf,
            phone=summary.user.phone,
            role=summary.user.role,
            project_id=summary.user.project_id,
            project_name=summary.project_name,
            department_id=summary.user.department_id,
            department_name=summary.department_name,
            avatar_url=summary.user.avatar_url,
            active=summary.user.active,
            first_access=summary.user.first_access,
            created_at=summary.user.created_at,
            updated_at=summary.user.updated_at,
        )
