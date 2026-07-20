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

    async def search_groups(
        self, query: str | None, project_ids: list[UUID] | None = None
    ) -> list[PermissionGroupSummary]:
        return await self._groups.search(query, project_ids)

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

    async def get_effective_permissions(self, user_id: UUID) -> list[ResourcePermission]:
        """Merges individual overrides with group-inherited permissions, OR-ing each
        operation per resource — this is what actually gates a user's access, unlike
        `get_user_permissions` which only returns their individual overrides.

        Mirrors the role short-circuits in `has_permission`: SUPER_ADMIN has no
        resource access at all (empty), ADMIN has full access to every resource,
        AUDITOR has read-only access to every resource. Only USER is actually
        governed by individual/group grants. Without this, the frontend's
        self-lookup (`GET /permissions/me`, used to gate the sidebar and buttons)
        would show ADMIN/AUDITOR as having no permissions at all, even though
        `has_permission` grants them full/read access on every real request."""
        user = await self._user_service.get_user(user_id)
        if user.role == Role.SUPER_ADMIN:
            return []
        if user.role == Role.ADMIN:
            return [
                ResourcePermission(resource=resource, can_create=True, can_read=True, can_update=True, can_delete=True)
                for resource in Resource
            ]
        if user.role == Role.AUDITOR:
            return [
                ResourcePermission(resource=resource, can_create=False, can_read=True, can_update=False, can_delete=False)
                for resource in Resource
            ]

        individual = await self._user_permissions.get_user_permissions(user_id)
        group_ids = await self._groups.get_group_ids_for_user(user_id)
        group_permissions = await self._user_permissions.get_permissions_for_groups(group_ids)

        merged: dict[Resource, ResourcePermission] = {}
        for permission in [*individual, *group_permissions]:
            existing = merged.get(permission.resource)
            if existing is None:
                merged[permission.resource] = ResourcePermission(
                    resource=permission.resource,
                    can_create=permission.can_create,
                    can_read=permission.can_read,
                    can_update=permission.can_update,
                    can_delete=permission.can_delete,
                )
            else:
                existing.can_create = existing.can_create or permission.can_create
                existing.can_read = existing.can_read or permission.can_read
                existing.can_update = existing.can_update or permission.can_update
                existing.can_delete = existing.can_delete or permission.can_delete
        return list(merged.values())

    async def set_user_permissions(self, user_id: UUID, permissions: list[ResourcePermissionSchema]) -> None:
        entries = [ResourcePermission(**permission.model_dump()) for permission in permissions]
        await self._user_permissions.set_user_permissions(user_id, entries)

    async def has_permission(self, user_id: UUID, resource: Resource, operation: PermissionOperation) -> bool:
        """SUPER_ADMIN has no tenant data access at all (not even read) — its
        role is limited to Organization management, gated separately by
        `require_roles`, not by this resource-permission system. ADMIN has
        full, unrestricted access within its own organization. AUDITOR can
        read anything in its organization but never create/update/delete,
        regardless of any group/individual grant. USER is governed entirely
        by individual + group-inherited permissions."""
        user = await self._user_service.get_user(user_id)
        if user.role == Role.SUPER_ADMIN:
            return False
        if user.role == Role.ADMIN:
            return True
        if user.role == Role.AUDITOR:
            return operation == PermissionOperation.READ

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
