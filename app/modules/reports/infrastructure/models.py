import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReportModel(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    project_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    filters_start_date: Mapped[date | None] = mapped_column(Date)
    filters_end_date: Mapped[date | None] = mapped_column(Date)
    filters_format: Mapped[str] = mapped_column(String(10), nullable=False, default="PDF")
    generated_by: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    file_key: Mapped[str | None] = mapped_column(String(500))
    file_size: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    filter_forms: Mapped[list["ReportFilterFormModel"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    filter_operators: Mapped[list["ReportFilterOperatorModel"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    filter_departments: Mapped[list["ReportFilterDepartmentModel"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ReportFilterFormModel(Base):
    """Normalized join row for a report's `form_ids` filter (forms live in MongoDB, so only the id is kept)."""

    __tablename__ = "report_filter_forms"

    report_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    form_id: Mapped[str] = mapped_column(String(24), primary_key=True)

    report: Mapped["ReportModel"] = relationship(back_populates="filter_forms")


class ReportFilterOperatorModel(Base):
    __tablename__ = "report_filter_operators"

    report_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    operator_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    report: Mapped["ReportModel"] = relationship(back_populates="filter_operators")


class ReportFilterDepartmentModel(Base):
    __tablename__ = "report_filter_departments"

    report_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True
    )

    report: Mapped["ReportModel"] = relationship(back_populates="filter_departments")
