from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.reports.domain.entities import ReportFormat, ReportStatus, ReportSummary, ReportType


class ReportFiltersRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    format: ReportFormat = ReportFormat.PDF
    form_ids: list[str] = Field(default_factory=list)
    operator_ids: list[UUID] = Field(default_factory=list)
    department_ids: list[UUID] = Field(default_factory=list)


class ReportGenerateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: ReportType
    description: str = ""
    project_id: UUID
    filters: ReportFiltersRequest


class ReportFiltersResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    format: ReportFormat
    form_ids: list[str]
    operator_ids: list[UUID]
    department_ids: list[UUID]


class ReportResponse(BaseModel):
    id: UUID
    name: str
    type: ReportType
    description: str
    project_id: UUID
    project_name: str
    filters: ReportFiltersResponse
    generated_by: UUID
    generated_by_name: str
    status: ReportStatus
    file_url: str | None
    file_size: str | None
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_summary(cls, summary: ReportSummary, file_url: str | None) -> "ReportResponse":
        report = summary.report
        return cls(
            id=report.id,
            name=report.name,
            type=report.type,
            description=report.description,
            project_id=report.project_id,
            project_name=summary.project_name,
            filters=ReportFiltersResponse(
                start_date=report.filters.start_date,
                end_date=report.filters.end_date,
                format=report.filters.format,
                form_ids=report.filters.form_ids,
                operator_ids=report.filters.operator_ids,
                department_ids=report.filters.department_ids,
            ),
            generated_by=report.generated_by,
            generated_by_name=summary.generated_by_name,
            status=report.status,
            file_url=file_url,
            file_size=report.file_size,
            created_at=report.created_at,
            completed_at=report.completed_at,
        )
