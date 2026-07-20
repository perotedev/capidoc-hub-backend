from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class DocStatus(StrEnum):
    NOT_GENERATED = "NOT_GENERATED"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    REVOKED = "REVOKED"


@dataclass(slots=True)
class DocumentTemplateEntity:
    id: UUID
    name: str
    description: str
    project_id: UUID
    header_logo_key: str | None
    footer_text: str
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class DocumentEntity:
    id: UUID
    attendance_id: str
    form_id: str
    form_name: str
    operator_id: UUID
    operator_name: str
    project_id: UUID
    template_id: UUID | None
    template_name: str | None
    status: DocStatus
    validation_code: str
    pdf_file_key: str | None
    generated_at: datetime | None
    revoked_at: datetime | None
    revoked_by: UUID | None
    revoke_reason: str | None
    created_at: datetime
    updated_at: datetime
