from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import FileUrlCacheServiceDep
from app.core.database import get_db_session
from app.core.storage import StorageService, get_storage_service
from app.modules.reports.application.services import ReportService
from app.modules.reports.domain.repositories import ReportRepository
from app.modules.reports.infrastructure.repository import SqlAlchemyReportRepository


def get_report_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ReportRepository:
    return SqlAlchemyReportRepository(session)


def get_report_service(
    repository: Annotated[ReportRepository, Depends(get_report_repository)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
    file_url_cache: FileUrlCacheServiceDep,
) -> ReportService:
    return ReportService(repository, storage, file_url_cache)


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
