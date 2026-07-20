from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.devices.domain.entities import (
    DeviceStatus,
    DeviceSummary,
    DownloadDetailStatus,
    DownloadStatus,
)
from app.shared.schema import CamelCaseModel


class DeviceRegisterRequest(CamelCaseModel):
    uid: str = Field(min_length=1, max_length=200)
    device_number: str = Field(min_length=1, max_length=50)
    license_last4: str = Field(min_length=4, max_length=4)
    project_id: UUID
    model: str
    os_version: str
    app_version: str


class DeviceUpdateRequest(CamelCaseModel):
    model: str | None = None
    os_version: str | None = None
    app_version: str | None = None
    status: DeviceStatus | None = None
    assigned_to: UUID | None = None
    require_journey_photo: bool | None = None
    require_journey_gps: bool | None = None


class DeviceResponse(CamelCaseModel):
    id: UUID
    uid: str
    device_number: str
    license_last4: str
    project_id: UUID
    project_name: str
    model: str
    os_version: str
    app_version: str
    last_sync: datetime | None
    status: DeviceStatus
    assigned_to: UUID | None
    assigned_to_name: str | None
    require_journey_photo: bool
    require_journey_gps: bool
    created_at: datetime

    @classmethod
    def from_summary(cls, summary: DeviceSummary) -> "DeviceResponse":
        return cls(
            id=summary.device.id,
            uid=summary.device.uid,
            device_number=summary.device.device_number,
            license_last4=summary.device.license_last4,
            project_id=summary.device.project_id,
            project_name=summary.project_name,
            model=summary.device.model,
            os_version=summary.device.os_version,
            app_version=summary.device.app_version,
            last_sync=summary.device.last_sync,
            status=summary.device.status,
            assigned_to=summary.device.assigned_to,
            assigned_to_name=summary.assigned_to_name,
            require_journey_photo=summary.device.require_journey_photo,
            require_journey_gps=summary.device.require_journey_gps,
            created_at=summary.device.created_at,
        )


class DeviceDownloadDetailCreateRequest(CamelCaseModel):
    form_id: str
    form_name: str
    records_count: int = 0
    status: DownloadDetailStatus


class DeviceDownloadCreateRequest(CamelCaseModel):
    forms_downloaded: int = 0
    records_uploaded: int = 0
    status: DownloadStatus
    duration: int = 0
    details: list[DeviceDownloadDetailCreateRequest] = Field(default_factory=list)


class DeviceDownloadDetailResponse(CamelCaseModel):
    form_id: str
    form_name: str
    records_count: int
    status: DownloadDetailStatus


class DeviceDownloadResponse(CamelCaseModel):
    id: UUID
    timestamp: datetime
    forms_downloaded: int
    records_uploaded: int
    status: DownloadStatus
    duration: int
    details: list[DeviceDownloadDetailResponse]


class DeviceDetailResponse(DeviceResponse):
    downloads: list[DeviceDownloadResponse]
