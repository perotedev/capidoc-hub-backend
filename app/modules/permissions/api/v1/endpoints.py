from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenancy import CurrentOrgProjectIds
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.modules.permissions.api.v1.dependencies import PermissionServiceDep
from app.modules.permissions.application.schemas import (
    PermissionGroupCreateRequest,
    PermissionGroupResponse,
    PermissionGroupUpdateRequest,
    ResourcePermissionSchema,
    SetGroupMembersRequest,
    SetGroupPermissionsRequest,
    SetUserPermissionsRequest,
)
from app.modules.users.api.v1.dependencies import UserServiceDep
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/permissions", tags=["Permissions"])


async def _assert_group_in_org(group_id: UUID, org_project_ids: list[UUID], service: PermissionServiceDep) -> None:
    group = await service.get_group(group_id)
    if group.project_id not in org_project_ids:
        raise NotFoundError(f"Permission group {group_id} not found")


async def _assert_user_in_org(user_id: UUID, org_project_ids: list[UUID], user_service: UserServiceDep) -> None:
    user = await user_service.get_user(user_id)
    if user.project_id not in org_project_ids:
        raise NotFoundError(f"User {user_id} not found")


@router.get("/groups", response_model=list[PermissionGroupResponse], dependencies=[require_permission(Resource.PERMISSAO, PermissionOperation.READ)])
async def search_groups(
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: PermissionServiceDep,
    query: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[PermissionGroupResponse]:
    if project_id is not None and project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    scope = [project_id] if project_id is not None else org_project_ids
    summaries = await service.search_groups(query, scope)
    return [PermissionGroupResponse.from_summary(summary) for summary in summaries]


@router.get("/groups/{group_id}", response_model=PermissionGroupResponse, dependencies=[require_permission(Resource.PERMISSAO, PermissionOperation.READ)])
async def get_group(
    group_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: PermissionServiceDep
) -> PermissionGroupResponse:
    await _assert_group_in_org(group_id, org_project_ids, service)
    summary = await service.get_group_summary(group_id)
    return PermissionGroupResponse.from_summary(summary)


@router.post("/groups", response_model=PermissionGroupResponse, status_code=201, dependencies=[require_permission(Resource.PERMISSAO, PermissionOperation.CREATE)])
async def create_group(
    request: PermissionGroupCreateRequest,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: PermissionServiceDep,
) -> PermissionGroupResponse:
    if request.project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    group = await service.create_group(request)
    summary = await service.get_group_summary(group.id)
    return PermissionGroupResponse.from_summary(summary)


@router.put("/groups/{group_id}", response_model=PermissionGroupResponse, dependencies=[require_permission(Resource.PERMISSAO, PermissionOperation.UPDATE)])
async def update_group(
    group_id: UUID,
    request: PermissionGroupUpdateRequest,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: PermissionServiceDep,
) -> PermissionGroupResponse:
    await _assert_group_in_org(group_id, org_project_ids, service)
    await service.update_group(group_id, request)
    summary = await service.get_group_summary(group_id)
    return PermissionGroupResponse.from_summary(summary)


@router.delete("/groups/{group_id}", status_code=204, dependencies=[require_permission(Resource.PERMISSAO, PermissionOperation.DELETE)])
async def delete_group(
    group_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: PermissionServiceDep
) -> None:
    await _assert_group_in_org(group_id, org_project_ids, service)
    await service.delete_group(group_id)


@router.put("/groups/{group_id}/permissions", status_code=204, dependencies=[require_permission(Resource.PERMISSAO, PermissionOperation.UPDATE)])
async def set_group_permissions(
    group_id: UUID,
    request: SetGroupPermissionsRequest,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: PermissionServiceDep,
) -> None:
    await _assert_group_in_org(group_id, org_project_ids, service)
    await service.set_group_permissions(group_id, request.permissions)


@router.put("/groups/{group_id}/members", status_code=204, dependencies=[require_permission(Resource.PERMISSAO, PermissionOperation.UPDATE)])
async def set_group_members(
    group_id: UUID,
    request: SetGroupMembersRequest,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: PermissionServiceDep,
) -> None:
    await _assert_group_in_org(group_id, org_project_ids, service)
    await service.set_group_members(group_id, request.user_ids)


@router.get("/me", response_model=list[ResourcePermissionSchema])
async def get_my_effective_permissions(
    current_user: CurrentUser, service: PermissionServiceDep
) -> list[ResourcePermissionSchema]:
    """Self-lookup of the caller's own merged (individual + group) permissions —
    what the frontend calls right after login to gate its own UI."""
    permissions = await service.get_effective_permissions(current_user.id)
    return [ResourcePermissionSchema(**asdict(permission)) for permission in permissions]


@router.get("/users/{user_id}", response_model=list[ResourcePermissionSchema], dependencies=[require_permission(Resource.PERMISSAO, PermissionOperation.READ)])
async def get_user_permissions(
    user_id: UUID,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: PermissionServiceDep,
    user_service: UserServiceDep,
) -> list[ResourcePermissionSchema]:
    await _assert_user_in_org(user_id, org_project_ids, user_service)
    permissions = await service.get_user_permissions(user_id)
    return [ResourcePermissionSchema(**asdict(permission)) for permission in permissions]


@router.put("/users/{user_id}", status_code=204, dependencies=[require_permission(Resource.PERMISSAO, PermissionOperation.UPDATE)])
async def set_user_permissions(
    user_id: UUID,
    request: SetUserPermissionsRequest,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: PermissionServiceDep,
    user_service: UserServiceDep,
) -> None:
    await _assert_user_in_org(user_id, org_project_ids, user_service)
    await service.set_user_permissions(user_id, request.permissions)
