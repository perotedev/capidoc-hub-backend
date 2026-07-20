from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.dashboards_custom.application.services import DashboardCustomService
from app.modules.dashboards_custom.domain.repositories import DashboardCustomRepository
from app.modules.dashboards_custom.infrastructure.repository import SqlAlchemyDashboardCustomRepository


def get_dashboard_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardCustomRepository:
    return SqlAlchemyDashboardCustomRepository(session)


def get_dashboard_service(
    repository: Annotated[DashboardCustomRepository, Depends(get_dashboard_repository)],
) -> DashboardCustomService:
    return DashboardCustomService(repository)


DashboardCustomServiceDep = Annotated[DashboardCustomService, Depends(get_dashboard_service)]
