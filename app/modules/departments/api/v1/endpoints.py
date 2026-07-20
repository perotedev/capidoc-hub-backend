from uuid import UUID

from fastapi import APIRouter, Query

from app.modules.auth.api.v1.dependencies import CurrentUser
from app.modules.departments.api.v1.dependencies import DepartmentServiceDep
from app.modules.departments.application.schemas import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
)

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=list[DepartmentResponse])
async def search_departments(
    _current_user: CurrentUser,
    service: DepartmentServiceDep,
    query: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[DepartmentResponse]:
    summaries = (
        await service.list_by_project(project_id) if project_id else await service.search(query)
    )
    return [DepartmentResponse.from_summary(summary) for summary in summaries]


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: UUID, _current_user: CurrentUser, service: DepartmentServiceDep
) -> DepartmentResponse:
    summary = await service.get_department_summary(department_id)
    return DepartmentResponse.from_summary(summary)


@router.post("", response_model=DepartmentResponse, status_code=201)
async def create_department(
    request: DepartmentCreateRequest, _current_user: CurrentUser, service: DepartmentServiceDep
) -> DepartmentResponse:
    department = await service.create_department(request)
    summary = await service.get_department_summary(department.id)
    return DepartmentResponse.from_summary(summary)


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: UUID,
    request: DepartmentUpdateRequest,
    _current_user: CurrentUser,
    service: DepartmentServiceDep,
) -> DepartmentResponse:
    await service.update_department(department_id, request)
    summary = await service.get_department_summary(department_id)
    return DepartmentResponse.from_summary(summary)


@router.delete("/{department_id}", status_code=204)
async def delete_department(
    department_id: UUID, _current_user: CurrentUser, service: DepartmentServiceDep
) -> None:
    await service.delete_department(department_id)
