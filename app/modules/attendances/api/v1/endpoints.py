from fastapi import APIRouter, Query

from app.modules.attendances.api.v1.dependencies import AttendanceServiceDep
from app.modules.attendances.application.schemas import AttendanceDetailResponse, AttendanceStatsResponse
from app.modules.attendances.domain.entities import AttendanceEntity
from app.modules.auth.api.v1.dependencies import CurrentUser

router = APIRouter(prefix="/attendances", tags=["Attendances"])


@router.get("", response_model=list[AttendanceEntity])
async def search_attendances(
    _current_user: CurrentUser,
    service: AttendanceServiceDep,
    query: str | None = Query(default=None),
    form_id: str | None = Query(default=None),
) -> list[AttendanceEntity]:
    return await service.search(query, form_id)


@router.get("/stats", response_model=AttendanceStatsResponse)
async def get_stats(
    _current_user: CurrentUser,
    service: AttendanceServiceDep,
    project_id: str | None = Query(default=None),
) -> AttendanceStatsResponse:
    return await service.get_stats(project_id)


@router.get("/by-form/{form_id}", response_model=list[AttendanceEntity])
async def search_by_form(
    form_id: str,
    _current_user: CurrentUser,
    service: AttendanceServiceDep,
    query: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    field_id: str | None = Query(default=None),
    field_value: str | None = Query(default=None),
) -> list[AttendanceEntity]:
    return await service.search_by_form(form_id, query, start_date, end_date, field_id, field_value)


@router.get("/{attendance_id}", response_model=AttendanceDetailResponse)
async def get_attendance(
    attendance_id: str, _current_user: CurrentUser, service: AttendanceServiceDep
) -> AttendanceDetailResponse:
    return await service.get_attendance(attendance_id)
