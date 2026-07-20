import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from app.core.cache import FileUrlCacheService
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.report_renderer import render_report_file
from app.core.storage import StorageService
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.notifications.application.services import NotificationService
from app.modules.notifications.domain.entities import NotificationType
from app.modules.reports.application.rendering import build_report_rows
from app.modules.reports.application.schemas import ReportGenerateRequest, ReportResponse
from app.modules.reports.domain.entities import (
    ReportEntity,
    ReportFilters,
    ReportStatus,
    ReportSummary,
    ReportType,
)
from app.modules.reports.domain.repositories import ReportRepository

logger = logging.getLogger(__name__)

_CONTENT_TYPE_BY_FORMAT = {
    "PDF": "application/pdf",
    "EXCEL": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "CSV": "text/csv",
}
_EXTENSION_BY_FORMAT = {"PDF": "pdf", "EXCEL": "xlsx", "CSV": "csv"}


class ReportService:
    """Orchestrates report *records* — the file itself is rendered outside this
    service (frontend or a dedicated export worker) and handed back for storage,
    exactly like the Documents module's PDF hand-off."""

    def __init__(
        self,
        repository: ReportRepository,
        storage: StorageService,
        file_url_cache: FileUrlCacheService,
        attendance_repository: AttendanceRepository,
        notification_service: NotificationService,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._file_url_cache = file_url_cache
        self._attendance_repository = attendance_repository
        self._notification_service = notification_service

    async def _to_response(self, summary: ReportSummary) -> ReportResponse:
        file_url = (
            await self._file_url_cache.get_signed_url(summary.report.file_key)
            if summary.report.file_key
            else None
        )
        return ReportResponse.from_summary(summary, file_url)

    async def _get_summary(self, report_id: UUID) -> ReportSummary:
        summary = await self._repository.get_summary_by_id(report_id)
        if summary is None:
            raise NotFoundError(f"Report {report_id} not found")
        return summary

    async def get_report(self, report_id: UUID) -> ReportResponse:
        return await self._to_response(await self._get_summary(report_id))

    async def search(self, query: str | None, type_: ReportType | None, project_id: UUID | None) -> list[ReportResponse]:
        summaries = await self._repository.search(query, type_, project_id)
        return [await self._to_response(summary) for summary in summaries]

    async def request_report(self, request: ReportGenerateRequest, generated_by: UUID) -> ReportResponse:
        report = ReportEntity(
            id=uuid.uuid4(),
            name=request.name,
            type=request.type,
            description=request.description,
            project_id=request.project_id,
            filters=ReportFilters(
                start_date=request.filters.start_date,
                end_date=request.filters.end_date,
                format=request.filters.format,
                form_ids=request.filters.form_ids,
                operator_ids=request.filters.operator_ids,
                department_ids=request.filters.department_ids,
            ),
            generated_by=generated_by,
            status=ReportStatus.GENERATING,
            file_key=None,
            file_size=None,
            created_at=datetime.now(timezone.utc),
            completed_at=None,
        )
        created = await self._repository.create(report)
        return await self.get_report(created.id)

    async def generate_report_file(self, report_id: UUID) -> None:
        """Actually renders the report file — scheduled as a `BackgroundTasks`
        job right after `request_report` returns, so the API response isn't
        blocked on the (synchronous) rendering work."""
        summary = await self._get_summary(report_id)
        report = summary.report
        try:
            if report.type == ReportType.AUDITORIA:
                # No audit-log module exists yet, so there is no real data to
                # report on — fail loudly instead of rendering an empty/fake file.
                raise BusinessRuleError("No audit-log data source is available yet")

            attendances = await self._attendance_repository.search_for_report(
                project_id=str(report.project_id),
                start_date=report.filters.start_date.isoformat() if report.filters.start_date else None,
                end_date=report.filters.end_date.isoformat() if report.filters.end_date else None,
                form_ids=report.filters.form_ids,
                operator_ids=[str(operator_id) for operator_id in report.filters.operator_ids],
            )
            title, headers, rows = build_report_rows(report.type, attendances)
            # PDF/XLSX rendering (PyMuPDF/openpyxl) is synchronous/CPU-bound —
            # offloaded to a thread so a big report doesn't block the event
            # loop (and every other in-flight request) while it renders.
            content = await run_in_threadpool(render_report_file, report.filters.format, title, headers, rows)
            await self.upload_generated_file(report_id, content)
            await self._notification_service.notify(
                report.generated_by,
                NotificationType.REPORT_READY,
                "Relatório pronto",
                f'O relatório "{report.name}" foi gerado e está disponível para download.',
                link="/painel/reports",
            )
        except Exception:
            logger.exception("Failed to generate report %s", report_id)
            await self.mark_error(report_id)
            await self._notification_service.notify(
                report.generated_by,
                NotificationType.REPORT_ERROR,
                "Falha ao gerar relatório",
                f'Não foi possível gerar o relatório "{report.name}".',
                link="/painel/reports",
            )

    async def upload_generated_file(self, report_id: UUID, content: bytes) -> ReportResponse:
        summary = await self._get_summary(report_id)
        report = summary.report
        if report.status == ReportStatus.READY:
            raise BusinessRuleError("This report has already been generated")

        extension = _EXTENSION_BY_FORMAT[report.filters.format.value]
        content_type = _CONTENT_TYPE_BY_FORMAT[report.filters.format.value]
        file_key = f"reports/{report.project_id}/{report.id}.{extension}"
        await self._storage.upload_file(file_key, content, content_type)

        report.file_key = file_key
        report.file_size = f"{len(content) / 1024:.1f} KB"
        report.status = ReportStatus.READY
        report.completed_at = datetime.now(timezone.utc)
        await self._repository.update(report)
        return await self.get_report(report_id)

    async def mark_error(self, report_id: UUID) -> ReportResponse:
        summary = await self._get_summary(report_id)
        report = summary.report
        report.status = ReportStatus.ERROR
        report.completed_at = datetime.now(timezone.utc)
        await self._repository.update(report)
        return await self.get_report(report_id)

    async def delete_report(self, report_id: UUID) -> None:
        summary = await self._get_summary(report_id)
        if summary.report.file_key:
            await self._storage.delete_file(summary.report.file_key)
        await self._repository.delete(report_id)
