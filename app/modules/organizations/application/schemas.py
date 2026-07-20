from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.modules.organizations.domain.entities import OrganizationSummary
from app.shared.schema import CamelCaseModel


class OrganizationCreateRequest(CamelCaseModel):
    name: str = Field(min_length=1, max_length=200)
    admin_name: str = Field(min_length=1, max_length=200)
    admin_email: EmailStr


class OrganizationUpdateRequest(CamelCaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    active: bool | None = None


class OrganizationResponse(CamelCaseModel):
    """Cross-tenant view for SUPER_ADMIN — metadata/counts only, never content."""

    id: UUID
    name: str
    admin_id: UUID
    admin_name: str
    admin_email: str
    active: bool
    projects_count: int
    users_count: int
    forms_count: int
    attendances_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_summary(cls, summary: OrganizationSummary) -> "OrganizationResponse":
        return cls(
            id=summary.organization.id,
            name=summary.organization.name,
            admin_id=summary.organization.admin_id,
            admin_name=summary.admin_name,
            admin_email=summary.admin_email,
            active=summary.organization.active,
            projects_count=summary.projects_count,
            users_count=summary.users_count,
            forms_count=summary.forms_count,
            attendances_count=summary.attendances_count,
            created_at=summary.organization.created_at,
            updated_at=summary.organization.updated_at,
        )
