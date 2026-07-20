from typing import Annotated

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.mongodb import get_mongo_db
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.attendances.infrastructure.mongo_repository import MongoAttendanceRepository
from app.modules.departments.domain.repositories import DepartmentRepository
from app.modules.departments.infrastructure.repository import SqlAlchemyDepartmentRepository
from app.modules.forms.api.v1.dependencies import get_form_repository
from app.modules.forms.domain.repositories import FormRepository
from app.modules.operators.application.services import OperatorService
from app.modules.projects.domain.repositories import ProjectRepository
from app.modules.projects.infrastructure.repository import SqlAlchemyProjectRepository
from app.modules.users.api.v1.dependencies import UserServiceDep


def _get_attendance_repository(database: Annotated[AsyncDatabase, Depends(get_mongo_db)]) -> AttendanceRepository:
    return MongoAttendanceRepository(database)


def _get_project_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ProjectRepository:
    return SqlAlchemyProjectRepository(session)


def _get_department_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DepartmentRepository:
    return SqlAlchemyDepartmentRepository(session)


def get_operator_service(
    user_service: UserServiceDep,
    attendance_repository: Annotated[AttendanceRepository, Depends(_get_attendance_repository)],
    project_repository: Annotated[ProjectRepository, Depends(_get_project_repository)],
    department_repository: Annotated[DepartmentRepository, Depends(_get_department_repository)],
    form_repository: Annotated[FormRepository, Depends(get_form_repository)],
) -> OperatorService:
    return OperatorService(
        user_service, attendance_repository, project_repository, department_repository, form_repository
    )


OperatorServiceDep = Annotated[OperatorService, Depends(get_operator_service)]
