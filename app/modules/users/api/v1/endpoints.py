from uuid import UUID

from fastapi import APIRouter, Query

from app.modules.auth.api.v1.dependencies import CurrentUser
from app.modules.users.api.v1.dependencies import UserServiceDep
from app.modules.users.application.schemas import UserCreateRequest, UserResponse, UserUpdateRequest
from app.shared.enums import Role

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserResponse])
async def search_users(
    _current_user: CurrentUser,
    service: UserServiceDep,
    query: str | None = Query(default=None),
    role: Role | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[UserResponse]:
    users = await service.search_users(query, role, project_id)
    return [UserResponse.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, _current_user: CurrentUser, service: UserServiceDep) -> UserResponse:
    user = await service.get_user(user_id)
    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    request: UserCreateRequest, _current_user: CurrentUser, service: UserServiceDep
) -> UserResponse:
    user = await service.create_user(request)
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID, request: UserUpdateRequest, _current_user: CurrentUser, service: UserServiceDep
) -> UserResponse:
    user = await service.update_user(user_id, request)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: UUID, _current_user: CurrentUser, service: UserServiceDep) -> None:
    await service.delete_user(user_id)
