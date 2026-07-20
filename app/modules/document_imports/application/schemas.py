from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.document_imports.domain.entities import DocumentImportStatus
from app.shared.schema import CamelCaseModel


class ExtractedFieldResponse(CamelCaseModel):
    field_id: str
    field_label: str
    value: str


class DocumentImportResponse(CamelCaseModel):
    id: UUID
    form_id: str
    form_name: str
    project_id: UUID
    status: DocumentImportStatus
    source_filename: str
    file_url: str | None
    extracted_fields: list[ExtractedFieldResponse]
    error_message: str | None
    attendance_id: str | None
    created_at: datetime
    updated_at: datetime


class DocumentImportCallbackField(CamelCaseModel):
    field_id: str
    value: str


class DocumentImportCallbackRequest(CamelCaseModel):
    """What n8n posts back to `/document-imports/{id}/callback` once its
    workflow finishes — either the extracted values, or an error message.

    Two shapes are accepted for the extracted data (use whichever your n8n
    node produces more naturally): `values` is a flat `{fieldId: value}`
    object — the natural output of a structured-output/JSON-schema AI node
    bound to the `extractionSchema` sent in the dispatch payload. `fields` is
    a list of `{fieldId, value}` pairs — simpler for a basic OCR/regex flow.
    Both may be sent together; they're merged."""

    fields: list[DocumentImportCallbackField] = Field(default_factory=list)
    values: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class DocumentImportConfirmField(CamelCaseModel):
    field_id: str
    field_label: str
    value: str


class DocumentImportConfirmRequest(CamelCaseModel):
    """The human-reviewed (possibly edited) field values — becomes the new
    attendance's `responses` verbatim."""

    responses: list[DocumentImportConfirmField]


class DocumentImportConfirmResponse(CamelCaseModel):
    attendance_id: str
