from typing import Protocol
from uuid import UUID

from app.modules.devices.domain.entities import (
    DeviceDownloadEntity,
    DeviceEntity,
    DeviceStatus,
    DeviceSummary,
)


class DeviceRepository(Protocol):
    async def get_by_id(self, device_id: UUID) -> DeviceEntity | None: ...

    async def get_summary_by_id(self, device_id: UUID) -> DeviceSummary | None: ...

    async def search(self, query: str | None, status: DeviceStatus | None) -> list[DeviceSummary]: ...

    async def create(self, device: DeviceEntity) -> DeviceEntity: ...

    async def update(self, device: DeviceEntity) -> DeviceEntity: ...

    async def delete(self, device_id: UUID) -> None: ...


class DeviceDownloadRepository(Protocol):
    async def list_by_device(self, device_id: UUID) -> list[DeviceDownloadEntity]: ...

    async def create(self, download: DeviceDownloadEntity) -> DeviceDownloadEntity: ...
