from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_imports.domain.entities import DocumentImportEntity, DocumentImportStatus, ExtractedField
from app.modules.document_imports.infrastructure.models import DocumentImportModel


def _to_entity(model: DocumentImportModel) -> DocumentImportEntity:
    return DocumentImportEntity(
        id=model.id,
        form_id=model.form_id,
        project_id=model.project_id,
        requested_by=model.requested_by,
        status=DocumentImportStatus(model.status),
        source_file_key=model.source_file_key,
        source_filename=model.source_filename,
        created_at=model.created_at,
        updated_at=model.updated_at,
        extracted_fields=[ExtractedField(field_id=item["fieldId"], value=item["value"]) for item in model.extracted_fields],
        error_message=model.error_message,
        attendance_id=model.attendance_id,
    )


class SqlAlchemyDocumentImportRepository:
    """Postgres-backed implementation of `DocumentImportRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, import_id: UUID) -> DocumentImportEntity | None:
        model = await self._session.get(DocumentImportModel, import_id)
        return _to_entity(model) if model else None

    async def create(self, document_import: DocumentImportEntity) -> DocumentImportEntity:
        model = DocumentImportModel(
            id=document_import.id,
            form_id=document_import.form_id,
            project_id=document_import.project_id,
            requested_by=document_import.requested_by,
            status=document_import.status.value,
            source_file_key=document_import.source_file_key,
            source_filename=document_import.source_filename,
            extracted_fields=[],
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, document_import: DocumentImportEntity) -> DocumentImportEntity:
        model = await self._session.get(DocumentImportModel, document_import.id)
        if model is None:
            raise ValueError(f"Document import {document_import.id} not found")
        model.status = document_import.status.value
        model.extracted_fields = [
            {"fieldId": item.field_id, "value": item.value} for item in document_import.extracted_fields
        ]
        model.error_message = document_import.error_message
        model.attendance_id = document_import.attendance_id
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)
