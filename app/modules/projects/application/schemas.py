from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.projects.domain.entities import ProjectSummary


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    cnpj: str | None = Field(default=None, max_length=20)
    admin_id: UUID | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    cnpj: str | None = None
    admin_id: UUID | None = None
    active: bool | None = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str
    cnpj: str | None
    admin_id: UUID | None
    admin_name: str | None
    users_count: int
    departments_count: int
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_summary(cls, summary: ProjectSummary) -> "ProjectResponse":
        return cls(
            id=summary.project.id,
            name=summary.project.name,
            description=summary.project.description,
            cnpj=summary.project.cnpj,
            admin_id=summary.project.admin_id,
            admin_name=summary.admin_name,
            users_count=summary.users_count,
            departments_count=summary.departments_count,
            active=summary.project.active,
            created_at=summary.project.created_at,
            updated_at=summary.project.updated_at,
        )
