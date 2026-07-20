from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.devices.application.services import DeviceService
from app.modules.devices.domain.repositories import DeviceDownloadRepository, DeviceRepository
from app.modules.devices.infrastructure.repository import (
    SqlAlchemyDeviceDownloadRepository,
    SqlAlchemyDeviceRepository,
)


def get_device_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> DeviceRepository:
    return SqlAlchemyDeviceRepository(session)


def get_device_download_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeviceDownloadRepository:
    return SqlAlchemyDeviceDownloadRepository(session)


def get_device_service(
    repository: Annotated[DeviceRepository, Depends(get_device_repository)],
    download_repository: Annotated[DeviceDownloadRepository, Depends(get_device_download_repository)],
) -> DeviceService:
    return DeviceService(repository, download_repository)


DeviceServiceDep = Annotated[DeviceService, Depends(get_device_service)]
