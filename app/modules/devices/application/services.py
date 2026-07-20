import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.devices.application.schemas import (
    DeviceDetailResponse,
    DeviceDownloadCreateRequest,
    DeviceDownloadDetailResponse,
    DeviceDownloadResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    DeviceUpdateRequest,
)
from app.modules.devices.domain.entities import (
    DeviceDownloadDetailEntity,
    DeviceDownloadEntity,
    DeviceEntity,
    DeviceStatus,
    DeviceSummary,
)
from app.modules.devices.domain.repositories import DeviceDownloadRepository, DeviceRepository


def _download_to_response(download: DeviceDownloadEntity) -> DeviceDownloadResponse:
    return DeviceDownloadResponse(
        id=download.id,
        timestamp=download.timestamp,
        forms_downloaded=download.forms_downloaded,
        records_uploaded=download.records_uploaded,
        status=download.status,
        duration=download.duration,
        details=[
            DeviceDownloadDetailResponse(
                form_id=detail.form_id,
                form_name=detail.form_name,
                records_count=detail.records_count,
                status=detail.status,
            )
            for detail in download.details
        ],
    )


class DeviceService:
    def __init__(self, repository: DeviceRepository, download_repository: DeviceDownloadRepository) -> None:
        self._repository = repository
        self._download_repository = download_repository

    async def _get_summary(self, device_id: UUID) -> DeviceSummary:
        summary = await self._repository.get_summary_by_id(device_id)
        if summary is None:
            raise NotFoundError(f"Device {device_id} not found")
        return summary

    async def get_device(self, device_id: UUID) -> DeviceResponse:
        summary = await self._get_summary(device_id)
        return DeviceResponse.from_summary(summary)

    async def get_device_detail(self, device_id: UUID) -> DeviceDetailResponse:
        summary = await self._get_summary(device_id)
        downloads = await self._download_repository.list_by_device(device_id)
        base = DeviceResponse.from_summary(summary)
        return DeviceDetailResponse(
            **base.model_dump(),
            downloads=[_download_to_response(download) for download in downloads],
        )

    async def search(self, query: str | None, status: DeviceStatus | None) -> list[DeviceResponse]:
        summaries = await self._repository.search(query, status)
        return [DeviceResponse.from_summary(summary) for summary in summaries]

    async def register_device(self, request: DeviceRegisterRequest) -> DeviceResponse:
        device = DeviceEntity(
            id=uuid.uuid4(),
            uid=request.uid,
            device_number=request.device_number,
            license_last4=request.license_last4,
            project_id=request.project_id,
            model=request.model,
            os_version=request.os_version,
            app_version=request.app_version,
            last_sync=None,
            status=DeviceStatus.INACTIVE,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
        )
        try:
            created = await self._repository.create(device)
        except IntegrityError as error:
            raise ConflictError(f"A device with uid {request.uid} or number {request.device_number} already exists") from error
        return await self.get_device(created.id)

    async def update_device(self, device_id: UUID, request: DeviceUpdateRequest) -> DeviceResponse:
        summary = await self._get_summary(device_id)
        device = summary.device
        if request.model is not None:
            device.model = request.model
        if request.os_version is not None:
            device.os_version = request.os_version
        if request.app_version is not None:
            device.app_version = request.app_version
        if request.status is not None:
            device.status = request.status
        if request.assigned_to is not None:
            device.assigned_to = request.assigned_to
        await self._repository.update(device)
        return await self.get_device(device_id)

    async def delete_device(self, device_id: UUID) -> None:
        await self._get_summary(device_id)
        await self._repository.delete(device_id)

    async def record_download(
        self, device_id: UUID, request: DeviceDownloadCreateRequest
    ) -> DeviceDownloadResponse:
        summary = await self._get_summary(device_id)
        download = DeviceDownloadEntity(
            id=uuid.uuid4(),
            device_id=device_id,
            timestamp=datetime.now(timezone.utc),
            forms_downloaded=request.forms_downloaded,
            records_uploaded=request.records_uploaded,
            status=request.status,
            duration=request.duration,
            details=[
                DeviceDownloadDetailEntity(
                    id=uuid.uuid4(),
                    form_id=detail.form_id,
                    form_name=detail.form_name,
                    records_count=detail.records_count,
                    status=detail.status,
                )
                for detail in request.details
            ],
        )
        created = await self._download_repository.create(download)

        device = summary.device
        device.last_sync = created.timestamp
        device.status = DeviceStatus.ONLINE
        await self._repository.update(device)

        return _download_to_response(created)
