from fastapi import APIRouter, Query

from app.core.tenancy import CurrentOrgProjectIds
from app.modules.attendances.api.v1.dependencies import AttendanceServiceDep
from app.modules.attendances.application.schemas import AttendanceDetailResponse, AttendanceStatsResponse
from app.modules.attendances.domain.entities import AttendanceEntity
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.core.exceptions import NotFoundError
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/attendances", tags=["Attendances"])


@router.get("", response_model=list[AttendanceEntity], dependencies=[require_permission(Resource.ATENDIMENTO, PermissionOperation.READ)])
async def search_attendances(
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: AttendanceServiceDep,
    query: str | None = Query(default=None),
    form_id: str | None = Query(default=None),
) -> list[AttendanceEntity]:
    allowed = {str(pid) for pid in org_project_ids}
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
    # No single project requested — aggregate across every project in the caller's org.
    stats_per_project = [await service.get_stats(pid) for pid in allowed] if allowed else []
    if not stats_per_project:
        return AttendanceStatsResponse(total=0, today=0, this_week=0, avg_duration=0, by_day=[])
    total = sum(stat.total for stat in stats_per_project)
    today = sum(stat.today for stat in stats_per_project)
    this_week = sum(stat.this_week for stat in stats_per_project)
    weighted_avg = (
        round(sum(stat.avg_duration * stat.total for stat in stats_per_project) / total) if total else 0
    )
    by_day_totals: dict[str, int] = {}
    for stat in stats_per_project:
        for entry in stat.by_day:
            by_day_totals[entry["date"]] = by_day_totals.get(entry["date"], 0) + entry["count"]
    by_day = [{"date": date, "count": count} for date, count in sorted(by_day_totals.items())]
    return AttendanceStatsResponse(total=total, today=today, this_week=this_week, avg_duration=weighted_avg, by_day=by_day)


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
