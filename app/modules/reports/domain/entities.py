from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class ReportType(StrEnum):
    ATENDIMENTOS = "ATENDIMENTOS"
    PRODUTIVIDADE = "PRODUTIVIDADE"
    ESTATISTICO = "ESTATISTICO"
    GEOGRAFICO = "GEOGRAFICO"
    TEMPO_EFICIENCIA = "TEMPO_EFICIENCIA"
    FOTOS = "FOTOS"
    AUDITORIA = "AUDITORIA"
    EXECUTIVO = "EXECUTIVO"


class ReportFormat(StrEnum):
    PDF = "PDF"
    EXCEL = "EXCEL"
    CSV = "CSV"


class ReportStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    ERROR = "error"


@dataclass(slots=True)
class ReportFilters:
    start_date: date | None
    end_date: date | None
    format: ReportFormat
    form_ids: list[str] = field(default_factory=list)
    operator_ids: list[UUID] = field(default_factory=list)
    department_ids: list[UUID] = field(default_factory=list)


@dataclass(slots=True)
class ReportEntity:
    id: UUID
    name: str
    type: ReportType
    description: str
    project_id: UUID
    filters: ReportFilters
    generated_by: UUID
    status: ReportStatus
    file_key: str | None
    file_size: str | None
    created_at: datetime
    completed_at: datetime | None


@dataclass(slots=True)
class ReportSummary:
    report: ReportEntity
    project_name: str
    generated_by_name: str
