from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.projects.domain.entities import ProjectSummary
from app.shared.schema import CamelCaseModel


class ProjectCreateRequest(CamelCaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    cnpj: str | None = Field(default=None, max_length=20)


class ProjectUpdateRequest(CamelCaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    cnpj: str | None = None
    active: bool | None = None


class ProjectResponse(CamelCaseModel):
    id: UUID
    name: str
    description: str
    cnpj: str | None
    org_id: UUID
    org_name: str
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
            org_id=summary.project.org_id,
            org_name=summary.org_name,
            users_count=summary.users_count,
            departments_count=summary.departments_count,
            active=summary.project.active,
            created_at=summary.project.created_at,
            updated_at=summary.project.updated_at,
        )
