from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.shared.enums import Role


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    cpf: str | None = Field(default=None, max_length=14)
    phone: str | None = Field(default=None, max_length=20)
    role: Role
    project_id: UUID | None = None
    department_id: UUID | None = None


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    cpf: str | None = Field(default=None, max_length=14)
    phone: str | None = Field(default=None, max_length=20)
    role: Role | None = None
    project_id: UUID | None = None
    department_id: UUID | None = None
    avatar_url: str | None = None
    active: bool | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
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
