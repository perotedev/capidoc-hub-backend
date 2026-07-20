from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import FileUrlCacheServiceDep
from app.core.database import get_db_session
from app.core.storage import StorageService, get_storage_service
from app.modules.attendances.api.v1.dependencies import get_attendance_repository
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.notifications.api.v1.dependencies import get_notification_service
from app.modules.notifications.application.services import NotificationService
from app.modules.reports.application.services import ReportService
from app.modules.reports.domain.repositories import ReportRepository
from app.modules.reports.infrastructure.repository import SqlAlchemyReportRepository


def get_report_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ReportRepository:
    return SqlAlchemyReportRepository(session)


def get_report_service(
    repository: Annotated[ReportRepository, Depends(get_report_repository)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
    file_url_cache: FileUrlCacheServiceDep,
    attendance_repository: Annotated[AttendanceRepository, Depends(get_attendance_repository)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> ReportService:
    return ReportService(repository, storage, file_url_cache, attendance_repository, notification_service)


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
