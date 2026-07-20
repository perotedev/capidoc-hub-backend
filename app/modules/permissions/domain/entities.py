from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.shared.enums import Resource


@dataclass(slots=True)
class ResourcePermission:
    resource: Resource
    can_create: bool
    can_read: bool
    can_update: bool
    can_delete: bool


@dataclass(slots=True)
class PermissionGroupEntity:
    id: UUID
    name: str
    description: str
    project_id: UUID
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class PermissionGroupSummary:
    group: PermissionGroupEntity
    project_name: str
    members_count: int
    permissions: list[ResourcePermission]
