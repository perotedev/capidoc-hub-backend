import secrets
import uuid
from datetime import datetime, timezone
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from app.core.cache import FileUrlCacheService
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.pdf_renderer import render_document_pdf
from app.core.storage import StorageService
from app.modules.attendances.domain.entities import AttendanceResponse
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.documents.application.schemas import (
    DocumentGenerateRequest,
    DocumentResponse,
    DocumentTemplateCreateRequest,
    DocumentTemplateResponse,
    DocumentTemplateUpdateRequest,
    DocumentValidationResponse,
)
from app.modules.documents.domain.entities import DocStatus, DocumentEntity, DocumentTemplateEntity
from app.modules.documents.domain.repositories import DocumentRepository, DocumentTemplateRepository
from app.modules.forms.domain.repositories import FormRepository


def _field_values_from_responses(responses: list[AttendanceResponse]) -> dict[str, str]:
    return {
        response.field_id: ", ".join(response.value) if isinstance(response.value, list) else response.value
        for response in responses
    }


def _generate_validation_code() -> str:
    raw = secrets.token_hex(6).upper()
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


def _template_to_response(template: DocumentTemplateEntity) -> DocumentTemplateResponse:
    return DocumentTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        project_id=template.project_id,
        header_logo_key=template.header_logo_key,
        footer_text=template.footer_text,
        active=template.active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


class DocumentTemplateService:
    def __init__(self, repository: DocumentTemplateRepository) -> None:
        self._repository = repository

    async def get_template(self, template_id: UUID) -> DocumentTemplateResponse:
        template = await self._repository.get_by_id(template_id)
        if template is None:
            raise NotFoundError(f"Document template {template_id} not found")
        return _template_to_response(template)

    async def list_by_project(self, project_id: UUID) -> list[DocumentTemplateResponse]:
        templates = await self._repository.list_by_project(project_id)
        return [_template_to_response(template) for template in templates]

    async def create_template(self, request: DocumentTemplateCreateRequest) -> DocumentTemplateResponse:
        now = datetime.now(timezone.utc)
        template = DocumentTemplateEntity(
            id=uuid.uuid4(),
            name=request.name,
            description=request.description,
            project_id=request.project_id,
            header_logo_key=request.header_logo_key,
            footer_text=request.footer_text,
            active=True,
            created_at=now,
            updated_at=now,
        )
        created = await self._repository.create(template)
        return _template_to_response(created)

    async def update_template(
        self, template_id: UUID, request: DocumentTemplateUpdateRequest
    ) -> DocumentTemplateResponse:
        template = await self._repository.get_by_id(template_id)
        if template is None:
            raise NotFoundError(f"Document template {template_id} not found")
        if request.name is not None:
            template.name = request.name
        if request.description is not None:
            template.description = request.description
        if request.header_logo_key is not None:
            template.header_logo_key = request.header_logo_key
        if request.footer_text is not None:
            template.footer_text = request.footer_text
        if request.active is not None:
            template.active = request.active
        updated = await self._repository.update(template)
        return _template_to_response(updated)

    async def delete_template(self, template_id: UUID) -> None:
        await self.get_template(template_id)
        await self._repository.delete(template_id)


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        template_repository: DocumentTemplateRepository,
        attendance_repository: AttendanceRepository,
        form_repository: FormRepository,
        storage: StorageService,
        file_url_cache: FileUrlCacheService,
    ) -> None:
        self._repository = repository
        self._template_repository = template_repository
        self._attendance_repository = attendance_repository
        self._form_repository = form_repository
        self._storage = storage
        self._file_url_cache = file_url_cache

    async def _to_response(self, document: DocumentEntity) -> DocumentResponse:
        pdf_url = (
            await self._file_url_cache.get_signed_url(document.pdf_file_key)
            if document.pdf_file_key
            else None
        )
        return DocumentResponse(
            id=document.id,
            attendance_id=document.attendance_id,
            form_id=document.form_id,
            form_name=document.form_name,
            operator_id=document.operator_id,
            operator_name=document.operator_name,
            project_id=document.project_id,
            template_id=document.template_id,
            template_name=document.template_name,
            status=document.status,
            validation_code=document.validation_code,
            pdf_url=pdf_url,
            generated_at=document.generated_at,
            revoked_at=document.revoked_at,
            revoked_by=document.revoked_by,
            revoke_reason=document.revoke_reason,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    async def get_document(self, document_id: UUID) -> DocumentResponse:
        document = await self._repository.get_by_id(document_id)
        if document is None:
            raise NotFoundError(f"Document {document_id} not found")
        return await self._to_response(document)

    async def get_by_attendance(self, attendance_id: str) -> DocumentResponse:
        document = await self._repository.get_by_attendance_id(attendance_id)
        if document is None:
            raise NotFoundError(f"No document registered for attendance {attendance_id}")
        return await self._to_response(document)

    async def search(
        self, query: str | None, status: DocStatus | None, project_id: UUID | None
    ) -> list[DocumentResponse]:
        documents = await self._repository.search(query, status, project_id)
        return [await self._to_response(document) for document in documents]

    async def register_document(self, request: DocumentGenerateRequest) -> DocumentResponse:
        existing = await self._repository.get_by_attendance_id(request.attendance_id)
        if existing is not None:
            raise ConflictError(f"A document already exists for attendance {request.attendance_id}")

        attendance = await self._attendance_repository.get_by_id(request.attendance_id)
        if attendance is None:
            raise NotFoundError(f"Attendance {request.attendance_id} not found")

        template_name: str | None = None
        if request.template_id is not None:
            template = await self._template_repository.get_by_id(request.template_id)
            if template is None:
                raise NotFoundError(f"Document template {request.template_id} not found")
            template_name = template.name

        now = datetime.now(timezone.utc)
        document = DocumentEntity(
            id=uuid.uuid4(),
            attendance_id=attendance.id,
            form_id=attendance.form_id,
            form_name=attendance.form_name,
            operator_id=UUID(attendance.operator_id),
            operator_name=attendance.operator_name,
            project_id=UUID(attendance.project_id),
            template_id=request.template_id,
            template_name=template_name,
            status=DocStatus.NOT_GENERATED,
            validation_code=_generate_validation_code(),
            pdf_file_key=None,
            generated_at=None,
            revoked_at=None,
            revoked_by=None,
            revoke_reason=None,
            created_at=now,
            updated_at=now,
        )
        created = await self._repository.create(document)
        generated = await self._try_auto_generate(created, request.template_id)
        return await self._to_response(generated)

    async def _try_auto_generate(self, document: DocumentEntity, template_id: UUID | None) -> DocumentEntity:
        """Renders the document immediately if its form has a template PDF and
        field layout configured; otherwise leaves it NOT_GENERATED for a manual
        upload via `upload_generated_pdf` later."""
        form = await self._form_repository.get_by_id(document.form_id)
        if form is None or form.template_pdf_file_key is None or not form.template:
            return document

        base_pdf_bytes = await self._storage.download_file(form.template_pdf_file_key)

        header_logo_bytes: bytes | None = None
        footer_text = ""
        if template_id is not None:
            template = await self._template_repository.get_by_id(template_id)
            if template is not None:
                footer_text = template.footer_text
                if template.header_logo_key:
                    header_logo_bytes = await self._storage.download_file(template.header_logo_key)

        attendance = await self._attendance_repository.get_by_id(document.attendance_id)
        field_values = _field_values_from_responses(attendance.responses) if attendance else {}

        # PyMuPDF rendering is synchronous/CPU-bound — offloaded to a thread so
        # it doesn't block the event loop (and every other in-flight request)
        # for the duration of the render, especially on a small single-core
        # instance under any concurrent load.
        pdf_bytes = await run_in_threadpool(
            render_document_pdf,
            base_pdf_bytes, form.template, field_values, header_logo_bytes, footer_text, document.validation_code,
        )

        file_key = f"documents/{document.project_id}/{document.id}.pdf"
        await self._storage.upload_file(file_key, pdf_bytes, "application/pdf")

        document.pdf_file_key = file_key
        document.status = DocStatus.GENERATED
        document.generated_at = datetime.now(timezone.utc)
        return await self._repository.update(document)

    async def upload_generated_pdf(self, document_id: UUID, content: bytes) -> DocumentResponse:
        document = await self._repository.get_by_id(document_id)
        if document is None:
            raise NotFoundError(f"Document {document_id} not found")
        if document.status == DocStatus.REVOKED:
            raise BusinessRuleError("Cannot upload a PDF for a revoked document")

        file_key = f"documents/{document.project_id}/{document.id}.pdf"
        await self._storage.upload_file(file_key, content, "application/pdf")

        document.pdf_file_key = file_key
        document.status = DocStatus.GENERATED
        document.generated_at = datetime.now(timezone.utc)
        updated = await self._repository.update(document)
        return await self._to_response(updated)

    async def revoke_document(self, document_id: UUID, revoked_by: UUID, reason: str) -> DocumentResponse:
        document = await self._repository.get_by_id(document_id)
        if document is None:
            raise NotFoundError(f"Document {document_id} not found")
        if document.status != DocStatus.GENERATED:
            raise BusinessRuleError("Only a generated document can be revoked")

        document.status = DocStatus.REVOKED
        document.revoked_at = datetime.now(timezone.utc)
        document.revoked_by = revoked_by
        document.revoke_reason = reason
        updated = await self._repository.update(document)
        return await self._to_response(updated)

    async def validate_code(self, validation_code: str) -> DocumentValidationResponse:
        document = await self._repository.get_by_validation_code(validation_code)
        if document is None or document.status == DocStatus.REVOKED:
            return DocumentValidationResponse(valid=False)
        return DocumentValidationResponse(
            valid=True,
            form_name=document.form_name,
            operator_name=document.operator_name,
            generated_at=document.generated_at,
            status=document.status,
        )
