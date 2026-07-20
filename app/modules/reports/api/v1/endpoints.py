from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile

from app.modules.auth.api.v1.dependencies import CurrentUser
from app.modules.reports.api.v1.dependencies import ReportServiceDep
from app.modules.reports.application.schemas import ReportGenerateRequest, ReportResponse
from app.modules.reports.domain.entities import ReportType

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=list[ReportResponse])
async def search_reports(
    _current_user: CurrentUser,
    service: ReportServiceDep,
    query: str | None = Query(default=None),
    type: ReportType | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[ReportResponse]:
    return await service.search(query, type, project_id)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: UUID, _current_user: CurrentUser, service: ReportServiceDep) -> ReportResponse:
    return await service.get_report(report_id)


@router.post("", response_model=ReportResponse, status_code=201)
async def request_report(
    request: ReportGenerateRequest, current_user: CurrentUser, service: ReportServiceDep
) -> ReportResponse:
    return await service.request_report(request, current_user.id)


@router.post("/{report_id}/file", response_model=ReportResponse)
async def upload_report_file(
    report_id: UUID,
    _current_user: CurrentUser,
    service: ReportServiceDep,
    file: UploadFile = File(...),
) -> ReportResponse:
    content = await file.read()
    return await service.upload_generated_file(report_id, content)


@router.post("/{report_id}/error", response_model=ReportResponse)
async def mark_report_error(report_id: UUID, _current_user: CurrentUser, service: ReportServiceDep) -> ReportResponse:
    return await service.mark_error(report_id)


@router.delete("/{report_id}", status_code=204)
async def delete_report(report_id: UUID, _current_user: CurrentUser, service: ReportServiceDep) -> None:
    await service.delete_report(report_id)
