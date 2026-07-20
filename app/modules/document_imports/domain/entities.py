from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class DocumentImportStatus(StrEnum):
    PENDING = "pending"  # dispatched to n8n, awaiting its callback
    EXTRACTED = "extracted"  # n8n returned data, awaiting human review + confirmation
    ERROR = "error"  # dispatch failed or n8n reported an extraction error
    CONFIRMED = "confirmed"  # reviewed and turned into a real attendance


@dataclass(slots=True)
class ExtractedField:
    field_id: str
    value: str


@dataclass(slots=True)
class DocumentImportEntity:
    id: UUID
    form_id: str
    project_id: UUID
    requested_by: UUID
    status: DocumentImportStatus
    source_file_key: str
    source_filename: str
    created_at: datetime
    updated_at: datetime
    extracted_fields: list[ExtractedField] = field(default_factory=list)
    error_message: str | None = None
    attendance_id: str | None = None
