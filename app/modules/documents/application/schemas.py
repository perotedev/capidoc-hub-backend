from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.documents.domain.entities import DocStatus


class DocumentTemplateCreateRequest(BaseModel):
    name: str
    description: str = ""
    project_id: UUID
    header_logo_key: str | None = None
    footer_text: str = ""


class DocumentTemplateUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    header_logo_key: str | None = None
    footer_text: str | None = None
    active: bool | None = None


class DocumentTemplateResponse(BaseModel):
    id: UUID
    name: str
    description: str
    project_id: UUID
    header_logo_key: str | None
    footer_text: str
    active: bool
    created_at: datetime
    updated_at: datetime


class DocumentGenerateRequest(BaseModel):
    """Registers a document for an already-completed attendance.

    The PDF itself is rendered outside this service (frontend or a dedicated
    rendering worker); this endpoint only receives the finished bytes and takes
    over storage, versioning and the public validation lookup from there on.
    """

    attendance_id: str
    template_id: UUID | None = None


class DocumentRevokeRequest(BaseModel):
    reason: str


class DocumentResponse(BaseModel):
    """API response for a document — like `DocumentEntity`, but with the PDF's
    S3 key resolved to a temporary signed URL (cached in Redis) when available."""

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
    pdf_url: str | None
    generated_at: datetime | None
    revoked_at: datetime | None
    revoked_by: UUID | None
    revoke_reason: str | None
    created_at: datetime
    updated_at: datetime


class DocumentValidationResponse(BaseModel):
    """Public-facing response for the no-auth validation-code lookup — deliberately
    excludes internal identifiers, exposing only what a third party should see."""

    valid: bool
    form_name: str | None = None
    operator_name: str | None = None
    generated_at: datetime | None = None
    status: DocStatus | None = None
