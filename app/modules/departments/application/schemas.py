from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.departments.domain.entities import DepartmentSummary
from app.shared.schema import CamelCaseModel


class DepartmentCreateRequest(CamelCaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    project_id: UUID
    parent_id: UUID | None = None


class DepartmentUpdateRequest(CamelCaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    parent_id: UUID | None = None
    active: bool | None = None


class DepartmentResponse(CamelCaseModel):
    id: UUID
    name: str
    description: str
    project_id: UUID
    project_name: str
    parent_id: UUID | None
    parent_name: str | None
    users_count: int
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_summary(cls, summary: DepartmentSummary) -> "DepartmentResponse":
        return cls(
            id=summary.department.id,
            name=summary.department.name,
            description=summary.department.description,
            project_id=summary.department.project_id,
            project_name=summary.project_name,
            parent_id=summary.department.parent_id,
            parent_name=summary.parent_name,
            users_count=summary.users_count,
            active=summary.department.active,
            created_at=summary.department.created_at,
            updated_at=summary.department.updated_at,
        )
