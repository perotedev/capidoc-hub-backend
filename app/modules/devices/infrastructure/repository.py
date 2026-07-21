from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.devices.domain.entities import (
    DeviceDownloadDetailEntity,
    DeviceDownloadEntity,
    DeviceEntity,
    DeviceStatus,
    DeviceSummary,
    DownloadDetailStatus,
    DownloadStatus,
)
from app.modules.devices.infrastructure.models import (
    DeviceDownloadDetailModel,
    DeviceDownloadModel,
    DeviceModel,
)
from app.modules.projects.infrastructure.models import ProjectModel
from app.modules.users.infrastructure.models import UserModel


def _device_to_entity(model: DeviceModel) -> DeviceEntity:
    return DeviceEntity(
        id=model.id,
        uid=model.uid,
        device_number=model.device_number,
        license_last4=model.license_last4,
        project_id=model.project_id,
        model=model.model,
        os_version=model.os_version,
        app_version=model.app_version,
        last_sync=model.last_sync,
        status=DeviceStatus(model.status),
        assigned_to=model.assigned_to,
        require_journey_photo=model.require_journey_photo,
        require_journey_gps=model.require_journey_gps,
        created_at=model.created_at,
    )


def _detail_to_entity(model: DeviceDownloadDetailModel) -> DeviceDownloadDetailEntity:
    return DeviceDownloadDetailEntity(
        id=model.id,
        form_id=model.form_id,
        form_name=model.form_name,
        records_count=model.records_count,
        status=DownloadDetailStatus(model.status),
    )


def _download_to_entity(model: DeviceDownloadModel) -> DeviceDownloadEntity:
    return DeviceDownloadEntity(
        id=model.id,
        device_id=model.device_id,
        timestamp=model.timestamp,
        forms_downloaded=model.forms_downloaded,
        records_uploaded=model.records_uploaded,
        status=DownloadStatus(model.status),
        duration=model.duration,
        details=[_detail_to_entity(detail) for detail in model.details],
    )


class SqlAlchemyDeviceRepository:
    """Postgres-backed implementation of `DeviceRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _summary_statement(self):
        return (
            select(DeviceModel, ProjectModel.name, UserModel.name)
            .join(ProjectModel, ProjectModel.id == DeviceModel.project_id)
            .outerjoin(UserModel, UserModel.id == DeviceModel.assigned_to)
        )

    async def get_by_id(self, device_id: UUID) -> DeviceEntity | None:
        model = await self._session.get(DeviceModel, device_id)
        return _device_to_entity(model) if model else None

    async def get_by_uid(self, uid: str) -> DeviceEntity | None:
        result = await self._session.execute(select(DeviceModel).where(DeviceModel.uid == uid))
        model = result.scalar_one_or_none()
        return _device_to_entity(model) if model else None

    async def get_summary_by_id(self, device_id: UUID) -> DeviceSummary | None:
        statement = self._summary_statement().where(DeviceModel.id == device_id)
        result = await self._session.execute(statement)
        row = result.first()
        if row is None:
            return None
        device_model, project_name, assigned_to_name = row
        return DeviceSummary(
            device=_device_to_entity(device_model),
            project_name=project_name,
            assigned_to_name=assigned_to_name,
        )

    async def search(
        self, query: str | None, status: DeviceStatus | None, project_ids: list[UUID] | None = None
    ) -> list[DeviceSummary]:
        statement = self._summary_statement()
        if project_ids is not None:
            statement = statement.where(DeviceModel.project_id.in_(project_ids))
        if status is not None:
            statement = statement.where(DeviceModel.status == status.value)
        if query:
            like_pattern = f"%{query}%"
            statement = statement.where(
                or_(DeviceModel.device_number.ilike(like_pattern), DeviceModel.model.ilike(like_pattern))
            )
        result = await self._session.execute(statement.order_by(DeviceModel.device_number))
        return [
            DeviceSummary(device=_device_to_entity(device_model), project_name=project_name, assigned_to_name=assigned_to_name)
            for device_model, project_name, assigned_to_name in result.all()
        ]

    async def create(self, device: DeviceEntity) -> DeviceEntity:
        model = DeviceModel(
            id=device.id,
            uid=device.uid,
            device_number=device.device_number,
            license_last4=device.license_last4,
            project_id=device.project_id,
            model=device.model,
            os_version=device.os_version,
            app_version=device.app_version,
            last_sync=device.last_sync,
            status=device.status.value,
            assigned_to=device.assigned_to,
            require_journey_photo=device.require_journey_photo,
            require_journey_gps=device.require_journey_gps,
        )
        self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise
        await self._session.refresh(model)
        return _device_to_entity(model)

    async def update(self, device: DeviceEntity) -> DeviceEntity:
        model = await self._session.get(DeviceModel, device.id)
        if model is None:
            raise ValueError(f"Device {device.id} not found")
        model.model = device.model
        model.os_version = device.os_version
        model.app_version = device.app_version
        model.project_id = device.project_id
        model.last_sync = device.last_sync
        model.status = device.status.value
        model.assigned_to = device.assigned_to
        model.require_journey_photo = device.require_journey_photo
        model.require_journey_gps = device.require_journey_gps
        await self._session.commit()
        await self._session.refresh(model)
        return _device_to_entity(model)

    async def delete(self, device_id: UUID) -> None:
        model = await self._session.get(DeviceModel, device_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()


class SqlAlchemyDeviceDownloadRepository:
    """Postgres-backed implementation of `DeviceDownloadRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_device(self, device_id: UUID) -> list[DeviceDownloadEntity]:
        statement = (
            select(DeviceDownloadModel)
            .where(DeviceDownloadModel.device_id == device_id)
            .options(selectinload(DeviceDownloadModel.details))
            .order_by(DeviceDownloadModel.timestamp.desc())
        )
        result = await self._session.execute(statement)
        return [_download_to_entity(model) for model in result.scalars().all()]

    async def create(self, download: DeviceDownloadEntity) -> DeviceDownloadEntity:
        model = DeviceDownloadModel(
            id=download.id,
            device_id=download.device_id,
            timestamp=download.timestamp,
            forms_downloaded=download.forms_downloaded,
            records_uploaded=download.records_uploaded,
            status=download.status.value,
            duration=download.duration,
            details=[
                DeviceDownloadDetailModel(
                    id=detail.id,
                    form_id=detail.form_id,
                    form_name=detail.form_name,
                    records_count=detail.records_count,
                    status=detail.status.value,
                )
                for detail in download.details
            ],
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model, attribute_names=["details"])
        return _download_to_entity(model)
