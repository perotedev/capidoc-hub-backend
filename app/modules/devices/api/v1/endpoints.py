from uuid import UUID

from fastapi import APIRouter, Query

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenancy import CurrentOrgProjectIds
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.modules.devices.api.v1.dependencies import DeviceServiceDep
from app.modules.devices.application.schemas import (
    DeviceDetailResponse,
    DeviceDownloadCreateRequest,
    DeviceDownloadResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    DeviceUpdateRequest,
)
from app.modules.devices.domain.entities import DeviceStatus
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=list[DeviceResponse], dependencies=[require_permission(Resource.DISPOSITIVO, PermissionOperation.READ)])
async def search_devices(
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: DeviceServiceDep,
    query: str | None = Query(default=None),
    status: DeviceStatus | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[DeviceResponse]:
    if project_id is not None and project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    scope = [project_id] if project_id is not None else org_project_ids
    return await service.search(query, status, scope)


@router.get("/{device_id}", response_model=DeviceDetailResponse, dependencies=[require_permission(Resource.DISPOSITIVO, PermissionOperation.READ)])
async def get_device(
    device_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: DeviceServiceDep
) -> DeviceDetailResponse:
    detail = await service.get_device_detail(device_id)
    if detail.project_id not in org_project_ids:
        raise NotFoundError(f"Device {device_id} not found")
    return detail


@router.post("", response_model=DeviceResponse, status_code=201)
async def register_device(
    request: DeviceRegisterRequest, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: DeviceServiceDep
) -> DeviceResponse:
    if request.project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    return await service.register_device(request)


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID, request: DeviceUpdateRequest, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: DeviceServiceDep
) -> DeviceResponse:
    current = await service.get_device(device_id)
    if current.project_id not in org_project_ids:
        raise NotFoundError(f"Device {device_id} not found")
    return await service.update_device(device_id, request)


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: DeviceServiceDep
) -> None:
    current = await service.get_device(device_id)
    if current.project_id not in org_project_ids:
        raise NotFoundError(f"Device {device_id} not found")
    await service.delete_device(device_id)


@router.post("/{device_id}/downloads", response_model=DeviceDownloadResponse, status_code=201)
async def record_download(
    device_id: UUID,
    request: DeviceDownloadCreateRequest,
    _current_user: CurrentUser,
    service: DeviceServiceDep,
) -> DeviceDownloadResponse:
    return await service.record_download(device_id, request)
