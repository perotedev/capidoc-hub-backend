from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.permissions.domain.entities import PermissionGroupSummary
from app.shared.enums import Resource


class ResourcePermissionSchema(BaseModel):
    resource: Resource
    can_create: bool = False
    can_read: bool = False
    can_update: bool = False
    can_delete: bool = False


class PermissionGroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    project_id: UUID


class PermissionGroupUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class SetGroupPermissionsRequest(BaseModel):
    permissions: list[ResourcePermissionSchema]


class SetGroupMembersRequest(BaseModel):
    user_ids: list[UUID]


class SetUserPermissionsRequest(BaseModel):
    permissions: list[ResourcePermissionSchema]


class PermissionGroupResponse(BaseModel):
    id: UUID
    name: str
    description: str
    project_id: UUID
    project_name: str
    members_count: int
    permissions: list[ResourcePermissionSchema]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_summary(cls, summary: PermissionGroupSummary) -> "PermissionGroupResponse":
        return cls(
            id=summary.group.id,
            name=summary.group.name,
            description=summary.group.description,
            project_id=summary.group.project_id,
            project_name=summary.project_name,
            members_count=summary.members_count,
            permissions=[ResourcePermissionSchema(**vars(permission)) for permission in summary.permissions],
            created_at=summary.group.created_at,
            updated_at=summary.group.updated_at,
        )
