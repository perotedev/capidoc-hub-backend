from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Query, UploadFile

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenancy import CurrentOrgProjectIds
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.modules.reports.api.v1.dependencies import ReportServiceDep
from app.modules.reports.application.schemas import ReportGenerateRequest, ReportResponse
from app.modules.reports.domain.entities import ReportType
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=list[ReportResponse], dependencies=[require_permission(Resource.RELATORIO, PermissionOperation.READ)])
async def search_reports(
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: ReportServiceDep,
    query: str | None = Query(default=None),
    type: ReportType | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[ReportResponse]:
    if project_id is not None:
        if project_id not in org_project_ids:
            raise ForbiddenError("That project does not belong to your organization")
        return await service.search(query, type, project_id)
    reports = await service.search(query, type, None)
    allowed = set(org_project_ids)
    return [report for report in reports if report.project_id in allowed]


@router.get("/{report_id}", response_model=ReportResponse, dependencies=[require_permission(Resource.RELATORIO, PermissionOperation.READ)])
async def get_report(
    report_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: ReportServiceDep
) -> ReportResponse:
    report = await service.get_report(report_id)
    if report.project_id not in org_project_ids:
        raise NotFoundError(f"Report {report_id} not found")
    return report


@router.post("", response_model=ReportResponse, status_code=201, dependencies=[require_permission(Resource.RELATORIO, PermissionOperation.CREATE)])
async def request_report(
    request: ReportGenerateRequest,
    current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: ReportServiceDep,
    background_tasks: BackgroundTasks,
) -> ReportResponse:
    if request.project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    report = await service.request_report(request, current_user.id)
    background_tasks.add_task(service.generate_report_file, report.id)
    return report


@router.post("/{report_id}/file", response_model=ReportResponse, dependencies=[require_permission(Resource.RELATORIO, PermissionOperation.CREATE)])
async def upload_report_file(
    report_id: UUID,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: ReportServiceDep,
    file: UploadFile = File(...),
) -> ReportResponse:
    report = await service.get_report(report_id)
    if report.project_id not in org_project_ids:
        raise NotFoundError(f"Report {report_id} not found")
    content = await file.read()
    return await service.upload_generated_file(report_id, content)


@router.post("/{report_id}/error", response_model=ReportResponse, dependencies=[require_permission(Resource.RELATORIO, PermissionOperation.CREATE)])
async def mark_report_error(
    report_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: ReportServiceDep
) -> ReportResponse:
    report = await service.get_report(report_id)
    if report.project_id not in org_project_ids:
        raise NotFoundError(f"Report {report_id} not found")
    return await service.mark_error(report_id)


@router.delete("/{report_id}", status_code=204, dependencies=[require_permission(Resource.RELATORIO, PermissionOperation.CREATE)])
async def delete_report(
    report_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: ReportServiceDep
) -> None:
    report = await service.get_report(report_id)
    if report.project_id not in org_project_ids:
        raise NotFoundError(f"Report {report_id} not found")
    await service.delete_report(report_id)
