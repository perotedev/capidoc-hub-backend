from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class DepartmentEntity:
    id: UUID
    name: str
    description: str
    project_id: UUID
    parent_id: UUID | None
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class DepartmentSummary:
    department: DepartmentEntity
    project_name: str
    parent_name: str | None
    users_count: int
