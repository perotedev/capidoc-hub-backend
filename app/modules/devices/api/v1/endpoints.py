from uuid import UUID

from fastapi import APIRouter, Query

from app.modules.auth.api.v1.dependencies import CurrentUser
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

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=list[DeviceResponse])
async def search_devices(
    _current_user: CurrentUser,
    service: DeviceServiceDep,
    query: str | None = Query(default=None),
    status: DeviceStatus | None = Query(default=None),
) -> list[DeviceResponse]:
    return await service.search(query, status)


@router.get("/{device_id}", response_model=DeviceDetailResponse)
async def get_device(device_id: UUID, _current_user: CurrentUser, service: DeviceServiceDep) -> DeviceDetailResponse:
    return await service.get_device_detail(device_id)


@router.post("", response_model=DeviceResponse, status_code=201)
async def register_device(
    request: DeviceRegisterRequest, _current_user: CurrentUser, service: DeviceServiceDep
) -> DeviceResponse:
    return await service.register_device(request)


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID, request: DeviceUpdateRequest, _current_user: CurrentUser, service: DeviceServiceDep
) -> DeviceResponse:
    return await service.update_device(device_id, request)


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: UUID, _current_user: CurrentUser, service: DeviceServiceDep) -> None:
    await service.delete_device(device_id)


@router.post("/{device_id}/downloads", response_model=DeviceDownloadResponse, status_code=201)
async def record_download(
    device_id: UUID,
    request: DeviceDownloadCreateRequest,
    _current_user: CurrentUser,
    service: DeviceServiceDep,
) -> DeviceDownloadResponse:
    return await service.record_download(device_id, request)
