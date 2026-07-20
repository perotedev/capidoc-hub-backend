from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.attendances.api.v1.dependencies import get_attendance_repository
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.forms.api.v1.dependencies import get_form_repository
from app.modules.forms.domain.repositories import FormRepository
from app.modules.organizations.application.services import OrganizationService
from app.modules.organizations.domain.repositories import OrganizationRepository
from app.modules.organizations.infrastructure.repository import SqlAlchemyOrganizationRepository
from app.modules.users.api.v1.dependencies import UserServiceDep


def get_organization_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrganizationRepository:
    return SqlAlchemyOrganizationRepository(session)


def get_organization_service(
    repository: Annotated[OrganizationRepository, Depends(get_organization_repository)],
    user_service: UserServiceDep,
    form_repository: Annotated[FormRepository, Depends(get_form_repository)],
    attendance_repository: Annotated[AttendanceRepository, Depends(get_attendance_repository)],
) -> OrganizationService:
    return OrganizationService(repository, user_service, form_repository, attendance_repository)


OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]
