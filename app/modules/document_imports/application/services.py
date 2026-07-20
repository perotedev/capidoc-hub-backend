import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

import httpx

from app.core.cache import FileUrlCacheService
from app.core.config import get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError, UnauthorizedError
from app.core.storage import StorageService
from app.modules.activities.application.services import ActivityService
from app.modules.activities.domain.entities import ActivityType
from app.modules.attendances.domain.entities import AttendanceEntity, AttendanceResponse
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.document_imports.application.extraction_schema import (
    build_extraction_json_schema,
    build_extraction_prompt,
    build_form_fields_payload,
)
from app.modules.document_imports.application.schemas import (
    DocumentImportCallbackRequest,
    DocumentImportConfirmField,
    DocumentImportConfirmResponse,
    DocumentImportResponse,
    ExtractedFieldResponse,
)
from app.modules.document_imports.domain.entities import DocumentImportEntity, DocumentImportStatus, ExtractedField
from app.modules.document_imports.domain.repositories import DocumentImportRepository
from app.modules.forms.application.services import FormService
from app.modules.forms.domain.entities import FormEntity
from app.modules.notifications.application.services import NotificationService
from app.modules.notifications.domain.entities import NotificationType
from app.modules.projects.domain.repositories import ProjectRepository

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentImportService:
    """Orchestrates the n8n document-extraction workflow: dispatches an
    uploaded PDF/image to n8n for OCR/AI extraction, receives the extracted
    field values back via callback, and — once a human confirms them — turns
    them into a real attendance."""

    def __init__(
        self,
        repository: DocumentImportRepository,
        storage: StorageService,
        file_url_cache: FileUrlCacheService,
        form_service: FormService,
        attendance_repository: AttendanceRepository,
        project_repository: ProjectRepository,
        notification_service: NotificationService,
        activity_service: ActivityService,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._file_url_cache = file_url_cache
        self._form_service = form_service
        self._attendance_repository = attendance_repository
        self._activity_service = activity_service
        self._project_repository = project_repository
        self._notification_service = notification_service

    async def request_import(
        self, form_id: str, project_id: UUID, user_id: UUID, filename: str, content: bytes, content_type: str
    ) -> DocumentImportResponse:
        form = await self._form_service.get_form(form_id)
        if form.project_id != str(project_id):
            raise NotFoundError(f"Form {form_id} not found")

        import_id = uuid.uuid4()
        extension = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        file_key = f"document-imports/{project_id}/{import_id}.{extension}"
        await self._storage.upload_file(file_key, content, content_type)

        now = datetime.now(timezone.utc)
        document_import = DocumentImportEntity(
            id=import_id,
            form_id=form_id,
            project_id=project_id,
            requested_by=user_id,
            status=DocumentImportStatus.PENDING,
            source_file_key=file_key,
            source_filename=filename,
            created_at=now,
            updated_at=now,
        )
        created = await self._repository.create(document_import)
        await self._dispatch_to_n8n(created, form)

        refreshed = await self._repository.get_by_id(created.id)
        assert refreshed is not None
        return await self._to_response(refreshed, form)

    async def _dispatch_to_n8n(self, document_import: DocumentImportEntity, form: FormEntity) -> None:
        if not settings.n8n_extraction_webhook_url:
            document_import.status = DocumentImportStatus.ERROR
            document_import.error_message = (
                "Integração com n8n não configurada (N8N_EXTRACTION_WEBHOOK_URL vazio)"
            )
            await self._repository.update(document_import)
            return

        file_url = await self._file_url_cache.get_signed_url(document_import.source_file_key)
        callback_url = (
            f"{settings.api_public_base_url}{settings.api_v1_prefix}"
            f"/document-imports/{document_import.id}/callback"
        )
        payload = {
            "importId": str(document_import.id),
            "formId": form.id,
            "formName": form.name,
            "fileUrl": file_url,
            "fileName": document_import.source_filename,
            "callbackUrl": callback_url,
            # The "template" of what to extract — dynamic per form. Pick whichever
            # matches your n8n node: `extractionSchema` is a ready-to-use JSON
            # Schema for a structured-output/function-calling AI node (keys =
            # field ids); `extractionPrompt` is a plain-text instruction for a
            # regular LLM prompt node. `formFields` is the raw field metadata in
            # case you need to build something custom.
            "formFields": build_form_fields_payload(form.fields),
            "extractionSchema": build_extraction_json_schema(form.fields),
            "extractionPrompt": build_extraction_prompt(form.name, form.fields),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings.n8n_extraction_webhook_url,
                    json=payload,
                    headers={"X-CapiDoc-Secret": settings.n8n_callback_secret},
                )
                response.raise_for_status()
        except Exception as error:
            logger.exception("Failed to dispatch document import %s to n8n", document_import.id)
            document_import.status = DocumentImportStatus.ERROR
            document_import.error_message = f"Falha ao enviar para o n8n: {error}"
            await self._repository.update(document_import)

    async def handle_callback(self, import_id: UUID, secret: str, request: DocumentImportCallbackRequest) -> None:
        if secret != settings.n8n_callback_secret:
            raise UnauthorizedError("Invalid callback secret")

        document_import = await self._repository.get_by_id(import_id)
        if document_import is None:
            raise NotFoundError(f"Document import {import_id} not found")
        if document_import.status != DocumentImportStatus.PENDING:
            raise BusinessRuleError(f"Document import {import_id} is not awaiting a callback")

        if request.error:
            document_import.status = DocumentImportStatus.ERROR
            document_import.error_message = request.error
        else:
            document_import.status = DocumentImportStatus.EXTRACTED
            document_import.extracted_fields = [
                ExtractedField(field_id=item.field_id, value=item.value) for item in request.fields
            ] + [ExtractedField(field_id=field_id, value=value) for field_id, value in request.values.items()]
        await self._repository.update(document_import)

        if request.error:
            await self._notification_service.notify(
                document_import.requested_by,
                NotificationType.DOCUMENT_IMPORT_ERROR,
                "Falha ao processar documento",
                f'Não foi possível extrair os dados de "{document_import.source_filename}": {request.error}',
                link="/painel/attendances",
            )
        else:
            await self._notification_service.notify(
                document_import.requested_by,
                NotificationType.DOCUMENT_IMPORT_EXTRACTED,
                "Documento processado",
                f'Os dados de "{document_import.source_filename}" foram extraídos. Revise antes de confirmar.',
                link=f"/painel/attendances/import/{document_import.id}",
            )

    async def get_import(self, import_id: UUID) -> DocumentImportResponse:
        document_import = await self._repository.get_by_id(import_id)
        if document_import is None:
            raise NotFoundError(f"Document import {import_id} not found")
        form = await self._form_service.get_form(document_import.form_id)
        return await self._to_response(document_import, form)

    async def confirm_import(
        self, import_id: UUID, user_id: UUID, user_name: str, responses: list[DocumentImportConfirmField]
    ) -> DocumentImportConfirmResponse:
        document_import = await self._repository.get_by_id(import_id)
        if document_import is None:
            raise NotFoundError(f"Document import {import_id} not found")
        if document_import.status != DocumentImportStatus.EXTRACTED:
            raise BusinessRuleError("This document import is not ready to be confirmed")

        form = await self._form_service.get_form(document_import.form_id)
        project = await self._project_repository.get_by_id(document_import.project_id)
        if project is None:
            raise NotFoundError(f"Project {document_import.project_id} not found")

        now = datetime.now(timezone.utc)
        attendance = AttendanceEntity(
            id="",
            form_id=form.id,
            form_name=form.name,
            operator_id=str(user_id),
            operator_name=user_name,
            project_id=str(document_import.project_id),
            project_name=project.name,
            duration=0,
            responses=[
                AttendanceResponse(field_id=item.field_id, field_label=item.field_label, value=item.value)
                for item in responses
            ],
            photos=[],
            signature=False,
            gps_location=None,
            created_at=now,
            completed_at=now,
            synced_at=now,
        )
        created = await self._attendance_repository.create(attendance)
        await self._form_service.notify_attendance_submitted(form.id)
        await self._activity_service.log(
            project.org_id,
            ActivityType.ATTENDANCE,
            "Atendimento registrado",
            f'{user_name} respondeu "{form.name}" via importação de documento',
            "file-up",
            user_id,
            user_name,
        )

        document_import.status = DocumentImportStatus.CONFIRMED
        document_import.attendance_id = created.id
        await self._repository.update(document_import)

        return DocumentImportConfirmResponse(attendance_id=created.id)

    async def _to_response(
        self, document_import: DocumentImportEntity, form: FormEntity | None
    ) -> DocumentImportResponse:
        file_url = await self._file_url_cache.get_signed_url(document_import.source_file_key)
        fields_by_id = {field.id: field.label for field in form.fields} if form else {}
        return DocumentImportResponse(
            id=document_import.id,
            form_id=document_import.form_id,
            form_name=form.name if form else "",
            project_id=document_import.project_id,
            status=document_import.status,
            source_filename=document_import.source_filename,
            file_url=file_url,
            extracted_fields=[
                ExtractedFieldResponse(
                    field_id=item.field_id,
                    field_label=fields_by_id.get(item.field_id, item.field_id),
                    value=item.value,
                )
                for item in document_import.extracted_fields
            ],
            error_message=document_import.error_message,
            attendance_id=document_import.attendance_id,
            created_at=document_import.created_at,
            updated_at=document_import.updated_at,
        )
