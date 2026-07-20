from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.departments.application.services import DepartmentService
from app.modules.departments.domain.repositories import DepartmentRepository
from app.modules.departments.infrastructure.repository import SqlAlchemyDepartmentRepository


def get_department_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DepartmentRepository:
    return SqlAlchemyDepartmentRepository(session)


def get_department_service(
    repository: Annotated[DepartmentRepository, Depends(get_department_repository)],
) -> DepartmentService:
    return DepartmentService(repository)


DepartmentServiceDep = Annotated[DepartmentService, Depends(get_department_service)]
