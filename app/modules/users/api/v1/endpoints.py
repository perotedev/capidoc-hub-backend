from uuid import UUID

from fastapi import APIRouter, Query

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenancy import CurrentOrgId
from app.modules.activities.api.v1.dependencies import ActivityServiceDep
from app.modules.activities.domain.entities import ActivityType
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.modules.projects.api.v1.dependencies import ProjectServiceDep
from app.modules.users.api.v1.dependencies import UserServiceDep
from app.modules.users.application.schemas import UserCreateRequest, UserResponse, UserUpdateRequest
from app.shared.enums import PermissionOperation, Resource, Role

router = APIRouter(prefix="/users", tags=["Users"])

_CREATABLE_BY: dict[Role, set[Role]] = {
    Role.SUPER_ADMIN: set(),  # SUPER_ADMIN creates ADMIN accounts only via POST /organizations
    Role.ADMIN: {Role.AUDITOR, Role.USER},
}


async def _org_project_ids(org_id: UUID, project_service: ProjectServiceDep) -> list[UUID]:
    summaries = await project_service.search(None, org_id)
    return [summary.project.id for summary in summaries]


@router.get("", response_model=list[UserResponse], dependencies=[require_permission(Resource.USUARIO, PermissionOperation.READ)])
async def search_users(
    _current_user: CurrentUser,
    org_id: CurrentOrgId,
    service: UserServiceDep,
    project_service: ProjectServiceDep,
    query: str | None = Query(default=None),
    role: Role | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[UserResponse]:
    allowed_project_ids = await _org_project_ids(org_id, project_service)
    if project_id is not None:
        if project_id not in allowed_project_ids:
            raise ForbiddenError("That project does not belong to your organization")
        allowed_project_ids = [project_id]
    summaries = await service.search_users_summary(query, role, allowed_project_ids)
    return [UserResponse.from_summary(summary) for summary in summaries]


@router.get("/{user_id}", response_model=UserResponse, dependencies=[require_permission(Resource.USUARIO, PermissionOperation.READ)])
async def get_user(
    user_id: UUID, _current_user: CurrentUser, org_id: CurrentOrgId, service: UserServiceDep, project_service: ProjectServiceDep
) -> UserResponse:
    summary = await service.get_user_summary(user_id)
    allowed_project_ids = await _org_project_ids(org_id, project_service)
    if summary.user.project_id not in allowed_project_ids:
        raise NotFoundError(f"User {user_id} not found")
    return UserResponse.from_summary(summary)


@router.post("", response_model=UserResponse, status_code=201, dependencies=[require_permission(Resource.USUARIO, PermissionOperation.CREATE)])
async def create_user(
    request: UserCreateRequest,
    current_user: CurrentUser,
    org_id: CurrentOrgId,
    service: UserServiceDep,
    project_service: ProjectServiceDep,
    activity_service: ActivityServiceDep,
) -> UserResponse:
    creatable = _CREATABLE_BY.get(current_user.role, set())
    if request.role not in creatable:
        raise ForbiddenError(f"A {current_user.role} cannot create a {request.role} account")

    if request.project_id is not None:
        allowed_project_ids = await _org_project_ids(org_id, project_service)
        if request.project_id not in allowed_project_ids:
            raise ForbiddenError("That project does not belong to your organization")

    user = await service.create_user(request)
    await activity_service.log(
        org_id,
        ActivityType.USER,
        "Usuário criado",
        f'{current_user.name} criou a conta de {user.name} ({user.role})',
        "user-plus",
        current_user.id,
        current_user.name,
    )
    return UserResponse.from_summary(await service.get_user_summary(user.id))


@router.put("/{user_id}", response_model=UserResponse, dependencies=[require_permission(Resource.USUARIO, PermissionOperation.UPDATE)])
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    current_user: CurrentUser,
    org_id: CurrentOrgId,
    service: UserServiceDep,
    project_service: ProjectServiceDep,
) -> UserResponse:
    target = await service.get_user(user_id)
    allowed_project_ids = await _org_project_ids(org_id, project_service)
    if target.project_id not in allowed_project_ids:
        raise NotFoundError(f"User {user_id} not found")

    if request.role is not None and request.role not in _CREATABLE_BY.get(current_user.role, set()):
        raise ForbiddenError(f"A {current_user.role} cannot assign the {request.role} role")
    if request.project_id is not None and request.project_id not in allowed_project_ids:
        raise ForbiddenError("That project does not belong to your organization")

    await service.update_user(user_id, request)
    return UserResponse.from_summary(await service.get_user_summary(user_id))


@router.delete("/{user_id}", status_code=204, dependencies=[require_permission(Resource.USUARIO, PermissionOperation.DELETE)])
async def delete_user(
    user_id: UUID, _current_user: CurrentUser, org_id: CurrentOrgId, service: UserServiceDep, project_service: ProjectServiceDep
) -> None:
    target = await service.get_user(user_id)
    allowed_project_ids = await _org_project_ids(org_id, project_service)
    if target.project_id not in allowed_project_ids:
        raise NotFoundError(f"User {user_id} not found")
    await service.delete_user(user_id)
