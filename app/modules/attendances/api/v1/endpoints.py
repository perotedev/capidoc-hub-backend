from fastapi import APIRouter, Query

from app.core.tenancy import CurrentOrgProjectIds
from app.modules.attendances.api.v1.dependencies import AttendanceServiceDep
from app.modules.attendances.application.schemas import AttendanceDetailResponse, AttendanceStatsResponse
from app.modules.attendances.domain.entities import AttendanceEntity
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.core.exceptions import ForbiddenError, NotFoundError
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/attendances", tags=["Attendances"])


@router.get("", response_model=list[AttendanceEntity], dependencies=[require_permission(Resource.ATENDIMENTO, PermissionOperation.READ)])
async def search_attendances(
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: AttendanceServiceDep,
    query: str | None = Query(default=None),
    form_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
) -> list[AttendanceEntity]:
    if project_id is not None and project_id not in {str(pid) for pid in org_project_ids}:
        raise ForbiddenError("That project does not belong to your organization")
    allowed = {project_id} if project_id is not None else {str(pid) for pid in org_project_ids}
    attendances = await service.search(query, form_id)
    return [attendance for attendance in attendances if attendance.project_id in allowed]


@router.get("/stats", response_model=AttendanceStatsResponse, dependencies=[require_permission(Resource.ATENDIMENTO, PermissionOperation.READ)])
async def get_stats(
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: AttendanceServiceDep,
    project_id: str | None = Query(default=None),
) -> AttendanceStatsResponse:
    allowed = {str(pid) for pid in org_project_ids}
    if project_id is not None:
        if project_id not in allowed:
            raise NotFoundError("Project not found")
        return await service.get_stats(project_id)
    if not allowed:
        return AttendanceStatsResponse(total=0, today=0, yesterday=0, this_week=0, last_week=0, avg_duration=0, by_day=[])
    # No single project requested — aggregate across every project in the caller's org in one query.
    return await service.get_stats(None, project_ids=list(allowed))


@router.get("/by-form/{form_id}", response_model=list[AttendanceEntity], dependencies=[require_permission(Resource.ATENDIMENTO, PermissionOperation.READ)])
async def search_by_form(
    form_id: str,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: AttendanceServiceDep,
    query: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    field_id: str | None = Query(default=None),
    field_value: str | None = Query(default=None),
) -> list[AttendanceEntity]:
    allowed = {str(pid) for pid in org_project_ids}
    attendances = await service.search_by_form(form_id, query, start_date, end_date, field_id, field_value)
    return [attendance for attendance in attendances if attendance.project_id in allowed]


@router.get("/{attendance_id}", response_model=AttendanceDetailResponse, dependencies=[require_permission(Resource.ATENDIMENTO, PermissionOperation.READ)])
async def get_attendance(
    attendance_id: str, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: AttendanceServiceDep
) -> AttendanceDetailResponse:
    detail = await service.get_attendance(attendance_id)
    allowed = {str(pid) for pid in org_project_ids}
    if detail.project_id not in allowed:
        raise NotFoundError(f"Attendance {attendance_id} not found")
    return detail
