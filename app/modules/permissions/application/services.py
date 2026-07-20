import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.modules.permissions.application.schemas import (
    PermissionGroupCreateRequest,
    PermissionGroupUpdateRequest,
    ResourcePermissionSchema,
)
from app.modules.permissions.domain.entities import PermissionGroupEntity, PermissionGroupSummary, ResourcePermission
from app.modules.permissions.domain.repositories import PermissionGroupRepository, UserPermissionRepository
from app.modules.users.application.services import UserService
from app.shared.enums import PermissionOperation, Resource, Role

_OPERATION_FIELD = {
    PermissionOperation.CREATE: "can_create",
    PermissionOperation.READ: "can_read",
    PermissionOperation.UPDATE: "can_update",
    PermissionOperation.DELETE: "can_delete",
}


class PermissionService:
    """Manages permission groups and evaluates a user's effective (group + individual) permissions."""

    def __init__(
        self,
        group_repository: PermissionGroupRepository,
        user_permission_repository: UserPermissionRepository,
        user_service: UserService,
    ) -> None:
        self._groups = group_repository
        self._user_permissions = user_permission_repository
        self._user_service = user_service

    async def get_group(self, group_id: UUID) -> PermissionGroupEntity:
        group = await self._groups.get_by_id(group_id)
        if group is None:
            raise NotFoundError(f"Permission group {group_id} not found")
        return group

    async def get_group_summary(self, group_id: UUID) -> PermissionGroupSummary:
        summary = await self._groups.get_summary_by_id(group_id)
        if summary is None:
            raise NotFoundError(f"Permission group {group_id} not found")
        return summary

    async def search_groups(self, query: str | None, project_id: UUID | None) -> list[PermissionGroupSummary]:
        return await self._groups.search(query, project_id)

    async def create_group(self, request: PermissionGroupCreateRequest) -> PermissionGroupEntity:
        now = datetime.now(timezone.utc)
        group = PermissionGroupEntity(
            id=uuid.uuid4(),
            name=request.name,
            description=request.description,
            project_id=request.project_id,
            created_at=now,
            updated_at=now,
        )
        return await self._groups.create(group)

    async def update_group(self, group_id: UUID, request: PermissionGroupUpdateRequest) -> PermissionGroupEntity:
        group = await self.get_group(group_id)
        if request.name is not None:
            group.name = request.name
        if request.description is not None:
            group.description = request.description
        return await self._groups.update(group)

    async def delete_group(self, group_id: UUID) -> None:
        await self.get_group(group_id)
        await self._groups.delete(group_id)

    async def set_group_permissions(self, group_id: UUID, permissions: list[ResourcePermissionSchema]) -> None:
        await self.get_group(group_id)
        entries = [ResourcePermission(**permission.model_dump()) for permission in permissions]
        await self._groups.set_group_permissions(group_id, entries)

    async def set_group_members(self, group_id: UUID, user_ids: list[UUID]) -> None:
        await self.get_group(group_id)
        await self._groups.set_members(group_id, user_ids)

    async def get_user_permissions(self, user_id: UUID) -> list[ResourcePermission]:
        return await self._user_permissions.get_user_permissions(user_id)

    async def set_user_permissions(self, user_id: UUID, permissions: list[ResourcePermissionSchema]) -> None:
        entries = [ResourcePermission(**permission.model_dump()) for permission in permissions]
        await self._user_permissions.set_user_permissions(user_id, entries)

    async def has_permission(self, user_id: UUID, resource: Resource, operation: PermissionOperation) -> bool:
        """Super admins bypass everything; otherwise merges individual + group-inherited permissions."""
        user = await self._user_service.get_user(user_id)
        if user.role == Role.SUPER_ADMIN:
            return True

        field_name = _OPERATION_FIELD[operation]

        individual = await self._user_permissions.get_user_permissions(user_id)
        for permission in individual:
            if permission.resource == resource and getattr(permission, field_name):
                return True

        group_ids = await self._groups.get_group_ids_for_user(user_id)
        group_permissions = await self._user_permissions.get_permissions_for_groups(group_ids)
        return any(
            permission.resource == resource and getattr(permission, field_name)
            for permission in group_permissions
        )
