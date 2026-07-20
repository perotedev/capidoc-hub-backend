import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeviceModel(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uid: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    device_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    license_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    os_version: Mapped[str] = mapped_column(String(50), nullable=False)
    app_version: Mapped[str] = mapped_column(String(50), nullable=False)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    require_journey_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    require_journey_gps: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    downloads: Mapped[list["DeviceDownloadModel"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class DeviceDownloadModel(Base):
    __tablename__ = "device_downloads"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    forms_downloaded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_uploaded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    device: Mapped["DeviceModel"] = relationship(back_populates="downloads")
    details: Mapped[list["DeviceDownloadDetailModel"]] = relationship(
        back_populates="download", cascade="all, delete-orphan"
    )


class DeviceDownloadDetailModel(Base):
    __tablename__ = "device_download_details"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    download_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("device_downloads.id", ondelete="CASCADE"), nullable=False
    )
    form_id: Mapped[str] = mapped_column(String(24), nullable=False)
    form_name: Mapped[str] = mapped_column(String(200), nullable=False)
    records_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    download: Mapped["DeviceDownloadModel"] = relationship(back_populates="details")
