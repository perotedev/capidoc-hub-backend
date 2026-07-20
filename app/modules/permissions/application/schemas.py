from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.permissions.domain.entities import PermissionGroupSummary
from app.shared.enums import Resource
from app.shared.schema import CamelCaseModel


class ResourcePermissionSchema(CamelCaseModel):
    resource: Resource
    can_create: bool = False
    can_read: bool = False
    can_update: bool = False
    can_delete: bool = False


class PermissionGroupCreateRequest(CamelCaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    project_id: UUID


class PermissionGroupUpdateRequest(CamelCaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class SetGroupPermissionsRequest(CamelCaseModel):
    permissions: list[ResourcePermissionSchema]


class SetGroupMembersRequest(CamelCaseModel):
    user_ids: list[UUID]


class SetUserPermissionsRequest(CamelCaseModel):
    permissions: list[ResourcePermissionSchema]


class PermissionGroupResponse(CamelCaseModel):
    id: UUID
    name: str
    description: str
    project_id: UUID
    project_name: str
    members_count: int
    member_ids: list[UUID]
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
            member_ids=summary.member_ids,
            permissions=[ResourcePermissionSchema(**asdict(permission)) for permission in summary.permissions],
            created_at=summary.group.created_at,
            updated_at=summary.group.updated_at,
        )
