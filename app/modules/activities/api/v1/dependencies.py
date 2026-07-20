from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.activities.application.services import ActivityService
from app.modules.activities.domain.repositories import ActivityRepository
from app.modules.activities.infrastructure.repository import SqlAlchemyActivityRepository
from app.modules.projects.api.v1.dependencies import get_project_repository
from app.modules.projects.domain.repositories import ProjectRepository


def get_activity_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ActivityRepository:
    return SqlAlchemyActivityRepository(session)


def get_activity_service(
    repository: Annotated[ActivityRepository, Depends(get_activity_repository)],
    project_repository: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> ActivityService:
    return ActivityService(repository, project_repository)


ActivityServiceDep = Annotated[ActivityService, Depends(get_activity_service)]
