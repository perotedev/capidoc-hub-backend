from uuid import UUID

from fastapi import APIRouter, Query

from app.modules.auth.api.v1.dependencies import CurrentUser
from app.modules.dashboards_custom.api.v1.dependencies import DashboardCustomServiceDep
from app.modules.dashboards_custom.application.schemas import (
    AddWidgetRequest,
    DashboardCreateRequest,
    DashboardResponse,
    DashboardUpdateRequest,
)

router = APIRouter(prefix="/dashboards-custom", tags=["Dashboards Custom"])


@router.get("", response_model=list[DashboardResponse])
async def list_dashboards(
    current_user: CurrentUser,
    service: DashboardCustomServiceDep,
    project_id: UUID | None = Query(default=None),
) -> list[DashboardResponse]:
    return await service.list_accessible(current_user.id, project_id)


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: UUID, current_user: CurrentUser, service: DashboardCustomServiceDep
) -> DashboardResponse:
    return await service.get_dashboard(dashboard_id, current_user.id)


@router.post("", response_model=DashboardResponse, status_code=201)
async def create_dashboard(
    request: DashboardCreateRequest, current_user: CurrentUser, service: DashboardCustomServiceDep
) -> DashboardResponse:
    return await service.create_dashboard(request, current_user.id)


@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: UUID,
    request: DashboardUpdateRequest,
    current_user: CurrentUser,
    service: DashboardCustomServiceDep,
) -> DashboardResponse:
    return await service.update_dashboard(dashboard_id, request, current_user.id)


@router.post("/{dashboard_id}/widgets", response_model=DashboardResponse, status_code=201)
async def add_widget(
    dashboard_id: UUID,
    request: AddWidgetRequest,
    current_user: CurrentUser,
    service: DashboardCustomServiceDep,
) -> DashboardResponse:
    return await service.add_widget(dashboard_id, request, current_user.id)


@router.delete("/{dashboard_id}/widgets/{widget_id}", response_model=DashboardResponse)
async def remove_widget(
    dashboard_id: UUID,
    widget_id: UUID,
    current_user: CurrentUser,
    service: DashboardCustomServiceDep,
) -> DashboardResponse:
    return await service.remove_widget(dashboard_id, widget_id, current_user.id)


@router.delete("/{dashboard_id}", status_code=204)
async def delete_dashboard(dashboard_id: UUID, current_user: CurrentUser, service: DashboardCustomServiceDep) -> None:
    await service.delete_dashboard(dashboard_id, current_user.id)
