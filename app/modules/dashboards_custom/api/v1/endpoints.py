from uuid import UUID

from fastapi import APIRouter, Query

from app.core.exceptions import ForbiddenError
from app.core.tenancy import CurrentOrgProjectIds
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.modules.dashboards_custom.api.v1.dependencies import DashboardCustomServiceDep
from app.modules.dashboards_custom.application.schemas import (
    AddWidgetRequest,
    DashboardCreateRequest,
    DashboardResponse,
    DashboardUpdateRequest,
)
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/dashboards-custom", tags=["Dashboards Custom"])


@router.get("", response_model=list[DashboardResponse], dependencies=[require_permission(Resource.DASHBOARD, PermissionOperation.READ)])
async def list_dashboards(
    current_user: CurrentUser,
    service: DashboardCustomServiceDep,
    project_id: UUID | None = Query(default=None),
) -> list[DashboardResponse]:
    return await service.list_accessible(current_user.id, project_id)


@router.get("/{dashboard_id}", response_model=DashboardResponse, dependencies=[require_permission(Resource.DASHBOARD, PermissionOperation.READ)])
async def get_dashboard(
    dashboard_id: UUID, current_user: CurrentUser, service: DashboardCustomServiceDep
) -> DashboardResponse:
    return await service.get_dashboard(dashboard_id, current_user.id)


@router.post("", response_model=DashboardResponse, status_code=201, dependencies=[require_permission(Resource.DASHBOARD, PermissionOperation.CREATE)])
async def create_dashboard(
    request: DashboardCreateRequest,
    current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: DashboardCustomServiceDep,
) -> DashboardResponse:
    if request.project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    return await service.create_dashboard(request, current_user.id)


@router.put("/{dashboard_id}", response_model=DashboardResponse, dependencies=[require_permission(Resource.DASHBOARD, PermissionOperation.UPDATE)])
async def update_dashboard(
    dashboard_id: UUID,
    request: DashboardUpdateRequest,
    current_user: CurrentUser,
    service: DashboardCustomServiceDep,
) -> DashboardResponse:
    return await service.update_dashboard(dashboard_id, request, current_user.id)


@router.post("/{dashboard_id}/widgets", response_model=DashboardResponse, status_code=201, dependencies=[require_permission(Resource.DASHBOARD, PermissionOperation.UPDATE)])
async def add_widget(
    dashboard_id: UUID,
    request: AddWidgetRequest,
    current_user: CurrentUser,
    service: DashboardCustomServiceDep,
) -> DashboardResponse:
    return await service.add_widget(dashboard_id, request, current_user.id)


@router.delete("/{dashboard_id}/widgets/{widget_id}", response_model=DashboardResponse, dependencies=[require_permission(Resource.DASHBOARD, PermissionOperation.UPDATE)])
async def remove_widget(
    dashboard_id: UUID,
    widget_id: UUID,
    current_user: CurrentUser,
    service: DashboardCustomServiceDep,
) -> DashboardResponse:
    return await service.remove_widget(dashboard_id, widget_id, current_user.id)


@router.delete("/{dashboard_id}", status_code=204, dependencies=[require_permission(Resource.DASHBOARD, PermissionOperation.DELETE)])
async def delete_dashboard(dashboard_id: UUID, current_user: CurrentUser, service: DashboardCustomServiceDep) -> None:
    await service.delete_dashboard(dashboard_id, current_user.id)
