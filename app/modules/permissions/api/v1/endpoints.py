from uuid import UUID

from fastapi import APIRouter, Query

from app.modules.auth.api.v1.dependencies import CurrentUser
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

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("/groups", response_model=list[PermissionGroupResponse])
async def search_groups(
    _current_user: CurrentUser,
    service: PermissionServiceDep,
    query: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[PermissionGroupResponse]:
    summaries = await service.search_groups(query, project_id)
    return [PermissionGroupResponse.from_summary(summary) for summary in summaries]


@router.get("/groups/{group_id}", response_model=PermissionGroupResponse)
async def get_group(group_id: UUID, _current_user: CurrentUser, service: PermissionServiceDep) -> PermissionGroupResponse:
    summary = await service.get_group_summary(group_id)
    return PermissionGroupResponse.from_summary(summary)


@router.post("/groups", response_model=PermissionGroupResponse, status_code=201)
async def create_group(
    request: PermissionGroupCreateRequest, _current_user: CurrentUser, service: PermissionServiceDep
) -> PermissionGroupResponse:
    group = await service.create_group(request)
    summary = await service.get_group_summary(group.id)
    return PermissionGroupResponse.from_summary(summary)


@router.put("/groups/{group_id}", response_model=PermissionGroupResponse)
async def update_group(
    group_id: UUID,
    request: PermissionGroupUpdateRequest,
    _current_user: CurrentUser,
    service: PermissionServiceDep,
) -> PermissionGroupResponse:
    await service.update_group(group_id, request)
    summary = await service.get_group_summary(group_id)
    return PermissionGroupResponse.from_summary(summary)


@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(group_id: UUID, _current_user: CurrentUser, service: PermissionServiceDep) -> None:
    await service.delete_group(group_id)


@router.put("/groups/{group_id}/permissions", status_code=204)
async def set_group_permissions(
    group_id: UUID, request: SetGroupPermissionsRequest, _current_user: CurrentUser, service: PermissionServiceDep
) -> None:
    await service.set_group_permissions(group_id, request.permissions)


@router.put("/groups/{group_id}/members", status_code=204)
async def set_group_members(
    group_id: UUID, request: SetGroupMembersRequest, _current_user: CurrentUser, service: PermissionServiceDep
) -> None:
    await service.set_group_members(group_id, request.user_ids)


@router.get("/users/{user_id}", response_model=list[ResourcePermissionSchema])
async def get_user_permissions(
    user_id: UUID, _current_user: CurrentUser, service: PermissionServiceDep
) -> list[ResourcePermissionSchema]:
    permissions = await service.get_user_permissions(user_id)
    return [ResourcePermissionSchema(**vars(permission)) for permission in permissions]


@router.put("/users/{user_id}", status_code=204)
async def set_user_permissions(
    user_id: UUID, request: SetUserPermissionsRequest, _current_user: CurrentUser, service: PermissionServiceDep
) -> None:
    await service.set_user_permissions(user_id, request.permissions)
