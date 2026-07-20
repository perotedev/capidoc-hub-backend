import random
import string
from datetime import datetime, timezone

from bson import ObjectId

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.storage import StorageService
from app.modules.forms.application.schemas import CreateFieldRequest, FormCreateRequest, FormRenameRequest
from app.modules.forms.domain.entities import FormEntity, FormField, FormSettings, FormStatus, TemplateBox
from app.modules.forms.domain.repositories import FormRepository

_OPTION_FIELD_TYPES = {"SELECT", "MULTI_SELECT", "CHECKBOX", "RADIO"}


def _random_suffix(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


class FormService:
    def __init__(self, repository: FormRepository, storage: StorageService) -> None:
        self._repository = repository
        self._storage = storage

    async def get_form(self, form_id: str) -> FormEntity:
        form = await self._repository.get_by_id(form_id)
        if form is None:
            raise NotFoundError(f"Form {form_id} not found")
        return form

    async def search(self, query: str | None, status: FormStatus | None, project_id: str | None) -> list[FormEntity]:
        return await self._repository.search(query, status, project_id)

    async def create_form(self, request: FormCreateRequest, created_by: str, created_by_name: str) -> FormEntity:
        now = datetime.now(timezone.utc)
        form = FormEntity(
            id=str(ObjectId()),
            name=request.name,
            description=request.description,
            project_id=request.project_id,
            status=FormStatus.DRAFT,
            version=1,
            fields=[],
            settings=FormSettings(),
            template=None,
            created_by=created_by,
            created_by_name=created_by_name,
            attendances_count=0,
            created_at=now,
            updated_at=now,
            published_at=None,
        )
        return await self._repository.create(form)

    async def rename_form(self, form_id: str, request: FormRenameRequest) -> None:
        await self.get_form(form_id)
        await self._repository.rename(form_id, request.name, request.description)

    async def add_field(self, form_id: str, request: CreateFieldRequest) -> FormField:
        form = await self.get_form(form_id)
        needs_options = request.type.value in _OPTION_FIELD_TYPES
        field = FormField(
            id=f"field-{int(now_ms())}-{_random_suffix(4)}",
            type=request.type,
            label="",
            description="",
            required=False,
            order=request.order,
            options=[{"id": "opt-1", "label": "Opção 1", "value": "opcao_1"}] if needs_options else [],
        )
        updated_fields = [*form.fields, field]
        await self._repository.update_fields(form_id, updated_fields)
        return field

    async def update_fields(self, form_id: str, fields: list[FormField]) -> None:
        await self.get_form(form_id)
        await self._repository.update_fields(form_id, fields)

    async def update_settings(self, form_id: str, settings: FormSettings) -> None:
        await self.get_form(form_id)
        await self._repository.update_settings(form_id, settings)

    async def update_template(self, form_id: str, template: list[TemplateBox]) -> None:
        await self.get_form(form_id)
        await self._repository.update_template(form_id, template)

    async def upload_template_pdf(self, form_id: str, content: bytes) -> FormEntity:
        if not content.startswith(b"%PDF"):
            raise BusinessRuleError("The uploaded file is not a valid PDF")
        await self.get_form(form_id)
        file_key = f"forms/{form_id}/template.pdf"
        await self._storage.upload_file(file_key, content, "application/pdf")
        await self._repository.update_template_pdf(form_id, file_key)
        return await self.get_form(form_id)

    async def get_template_pdf(self, form_id: str) -> bytes:
        form = await self.get_form(form_id)
        if form.template_pdf_file_key is None:
            raise NotFoundError(f"Form {form_id} has no template PDF uploaded")
        return await self._storage.download_file(form.template_pdf_file_key)

    async def publish(self, form_id: str) -> None:
        await self.get_form(form_id)
        await self._repository.set_status(form_id, FormStatus.PUBLISHED)

    async def archive(self, form_id: str) -> None:
        await self.get_form(form_id)
        await self._repository.set_status(form_id, FormStatus.ARCHIVED)

    async def duplicate(self, form_id: str, created_by: str, created_by_name: str) -> FormEntity:
        original = await self.get_form(form_id)
        now = datetime.now(timezone.utc)
        copy = original.model_copy(
            update={
                "id": str(ObjectId()),
                "name": f"{original.name} (Cópia)",
                "status": FormStatus.DRAFT,
                "version": 1,
                "attendances_count": 0,
                "created_by": created_by,
                "created_by_name": created_by_name,
                "created_at": now,
                "updated_at": now,
                "published_at": None,
            }
        )
        return await self._repository.create(copy)

    async def delete_form(self, form_id: str) -> None:
        await self.get_form(form_id)
        await self._repository.delete(form_id)

    async def notify_attendance_submitted(self, form_id: str) -> None:
        await self._repository.increment_attendances_count(form_id)


def now_ms() -> float:
    return datetime.now(timezone.utc).timestamp() * 1000
