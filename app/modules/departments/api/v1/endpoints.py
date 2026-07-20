from uuid import UUID

from fastapi import APIRouter, Query

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenancy import CurrentOrgProjectIds
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.modules.departments.api.v1.dependencies import DepartmentServiceDep
from app.modules.departments.application.schemas import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
)
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=list[DepartmentResponse], dependencies=[require_permission(Resource.DEPARTAMENTO, PermissionOperation.READ)])
async def search_departments(
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: DepartmentServiceDep,
    query: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[DepartmentResponse]:
    if project_id is not None and project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    scope = [project_id] if project_id is not None else org_project_ids
    summaries = await service.search(query, scope)
    return [DepartmentResponse.from_summary(summary) for summary in summaries]


@router.get("/{department_id}", response_model=DepartmentResponse, dependencies=[require_permission(Resource.DEPARTAMENTO, PermissionOperation.READ)])
async def get_department(
    department_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: DepartmentServiceDep
) -> DepartmentResponse:
    summary = await service.get_department_summary(department_id)
    if summary.department.project_id not in org_project_ids:
        raise NotFoundError(f"Department {department_id} not found")
    return DepartmentResponse.from_summary(summary)


@router.post("", response_model=DepartmentResponse, status_code=201, dependencies=[require_permission(Resource.DEPARTAMENTO, PermissionOperation.CREATE)])
async def create_department(
    request: DepartmentCreateRequest, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: DepartmentServiceDep
) -> DepartmentResponse:
    if request.project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    department = await service.create_department(request)
    summary = await service.get_department_summary(department.id)
    return DepartmentResponse.from_summary(summary)


@router.put("/{department_id}", response_model=DepartmentResponse, dependencies=[require_permission(Resource.DEPARTAMENTO, PermissionOperation.UPDATE)])
async def update_department(
    department_id: UUID,
    request: DepartmentUpdateRequest,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: DepartmentServiceDep,
) -> DepartmentResponse:
    summary = await service.get_department_summary(department_id)
    if summary.department.project_id not in org_project_ids:
        raise NotFoundError(f"Department {department_id} not found")
    await service.update_department(department_id, request)
    updated_summary = await service.get_department_summary(department_id)
    return DepartmentResponse.from_summary(updated_summary)


@router.delete("/{department_id}", status_code=204, dependencies=[require_permission(Resource.DEPARTAMENTO, PermissionOperation.DELETE)])
async def delete_department(
    department_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: DepartmentServiceDep
) -> None:
    summary = await service.get_department_summary(department_id)
    if summary.department.project_id not in org_project_ids:
        raise NotFoundError(f"Department {department_id} not found")
    await service.delete_department(department_id)
