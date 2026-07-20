from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class DeviceStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    INACTIVE = "inactive"


class DownloadStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class DownloadDetailStatus(StrEnum):
    SYNCED = "synced"
    PENDING = "pending"
    ERROR = "error"


@dataclass(slots=True)
class DeviceDownloadDetailEntity:
    id: UUID
    form_id: str
    form_name: str
    records_count: int
    status: DownloadDetailStatus


@dataclass(slots=True)
class DeviceDownloadEntity:
    id: UUID
    device_id: UUID
    timestamp: datetime
    forms_downloaded: int
    records_uploaded: int
    status: DownloadStatus
    duration: int
    details: list[DeviceDownloadDetailEntity] = field(default_factory=list)


@dataclass(slots=True)
class DeviceEntity:
    id: UUID
    uid: str
    device_number: str
    license_last4: str
    project_id: UUID
    model: str
    os_version: str
    app_version: str
    last_sync: datetime | None
    status: DeviceStatus
    assigned_to: UUID | None
    created_at: datetime


@dataclass(slots=True)
class DeviceSummary:
    device: DeviceEntity
    project_name: str
    assigned_to_name: str | None
