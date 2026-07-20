from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class ProjectEntity:
    id: UUID
    name: str
    description: str
    cnpj: str | None
    org_id: UUID
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ProjectSummary:
    """A project enriched with counts/denormalized names for API responses."""

    project: ProjectEntity
    org_name: str
    users_count: int
    departments_count: int
