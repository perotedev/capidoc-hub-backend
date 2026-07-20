from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class OrganizationEntity:
    id: UUID
    name: str
    admin_id: UUID
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class OrganizationSummary:
    """Cross-tenant view for SUPER_ADMIN — metadata/counts only, never content."""

    organization: OrganizationEntity
    admin_name: str
    admin_email: str
    projects_count: int
    users_count: int
    forms_count: int
    attendances_count: int
