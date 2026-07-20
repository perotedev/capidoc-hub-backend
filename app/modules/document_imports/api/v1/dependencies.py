from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import FileUrlCacheServiceDep
from app.core.database import get_db_session
from app.core.storage import StorageService, get_storage_service
from app.modules.activities.api.v1.dependencies import get_activity_service
from app.modules.activities.application.services import ActivityService
from app.modules.attendances.api.v1.dependencies import get_attendance_repository
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.document_imports.application.services import DocumentImportService
from app.modules.document_imports.domain.repositories import DocumentImportRepository
from app.modules.document_imports.infrastructure.repository import SqlAlchemyDocumentImportRepository
from app.modules.forms.api.v1.dependencies import FormServiceDep
from app.modules.notifications.api.v1.dependencies import get_notification_service
from app.modules.notifications.application.services import NotificationService
from app.modules.projects.api.v1.dependencies import get_project_repository
from app.modules.projects.domain.repositories import ProjectRepository


def get_document_import_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentImportRepository:
    return SqlAlchemyDocumentImportRepository(session)


def get_document_import_service(
    repository: Annotated[DocumentImportRepository, Depends(get_document_import_repository)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
    file_url_cache: FileUrlCacheServiceDep,
    form_service: FormServiceDep,
    attendance_repository: Annotated[AttendanceRepository, Depends(get_attendance_repository)],
    project_repository: Annotated[ProjectRepository, Depends(get_project_repository)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
    activity_service: Annotated[ActivityService, Depends(get_activity_service)],
) -> DocumentImportService:
    return DocumentImportService(
        repository, storage, file_url_cache, form_service, attendance_repository,
        project_repository, notification_service, activity_service,
    )


DocumentImportServiceDep = Annotated[DocumentImportService, Depends(get_document_import_service)]
