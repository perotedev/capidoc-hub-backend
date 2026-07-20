from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.projects.application.services import ProjectService
from app.modules.projects.domain.repositories import ProjectRepository
from app.modules.projects.infrastructure.repository import SqlAlchemyProjectRepository


def get_project_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ProjectRepository:
    return SqlAlchemyProjectRepository(session)


def get_project_service(
    repository: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> ProjectService:
    return ProjectService(repository)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
