from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import FileUrlCacheServiceDep
from app.core.database import get_db_session
from app.core.storage import StorageService, get_storage_service
from app.modules.attendances.api.v1.dependencies import get_attendance_repository
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.documents.application.services import DocumentService, DocumentTemplateService
from app.modules.documents.domain.repositories import DocumentRepository, DocumentTemplateRepository
from app.modules.documents.infrastructure.repository import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentTemplateRepository,
)
from app.modules.forms.api.v1.dependencies import get_form_repository
from app.modules.forms.domain.repositories import FormRepository


def get_document_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> DocumentRepository:
    return SqlAlchemyDocumentRepository(session)


def get_document_template_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentTemplateRepository:
    return SqlAlchemyDocumentTemplateRepository(session)


def get_document_template_service(
    repository: Annotated[DocumentTemplateRepository, Depends(get_document_template_repository)],
) -> DocumentTemplateService:
    return DocumentTemplateService(repository)


def get_document_service(
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    template_repository: Annotated[DocumentTemplateRepository, Depends(get_document_template_repository)],
    attendance_repository: Annotated[AttendanceRepository, Depends(get_attendance_repository)],
    form_repository: Annotated[FormRepository, Depends(get_form_repository)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
    file_url_cache: FileUrlCacheServiceDep,
) -> DocumentService:
    return DocumentService(
        repository, template_repository, attendance_repository, form_repository, storage, file_url_cache
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
DocumentTemplateServiceDep = Annotated[DocumentTemplateService, Depends(get_document_template_service)]
