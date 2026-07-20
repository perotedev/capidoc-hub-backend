from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.permissions.application.services import PermissionService
from app.modules.permissions.domain.repositories import PermissionGroupRepository, UserPermissionRepository
from app.modules.permissions.infrastructure.repository import SqlAlchemyPermissionRepository
from app.modules.users.api.v1.dependencies import UserServiceDep


def get_permission_group_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PermissionGroupRepository:
    return SqlAlchemyPermissionRepository(session)


def get_user_permission_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserPermissionRepository:
    return SqlAlchemyPermissionRepository(session)


def get_permission_service(
    group_repository: Annotated[PermissionGroupRepository, Depends(get_permission_group_repository)],
    user_permission_repository: Annotated[UserPermissionRepository, Depends(get_user_permission_repository)],
    user_service: UserServiceDep,
) -> PermissionService:
    return PermissionService(group_repository, user_permission_repository, user_service)


PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]
