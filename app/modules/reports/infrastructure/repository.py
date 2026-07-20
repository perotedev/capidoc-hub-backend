from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.projects.infrastructure.models import ProjectModel
from app.modules.reports.domain.entities import (
    ReportEntity,
    ReportFilters,
    ReportFormat,
    ReportStatus,
    ReportSummary,
    ReportType,
)
from app.modules.reports.infrastructure.models import (
    ReportFilterDepartmentModel,
    ReportFilterFormModel,
    ReportFilterOperatorModel,
    ReportModel,
)
from app.modules.users.infrastructure.models import UserModel


def _to_entity(model: ReportModel) -> ReportEntity:
    return ReportEntity(
        id=model.id,
        name=model.name,
        type=ReportType(model.type),
        description=model.description,
        project_id=model.project_id,
        filters=ReportFilters(
            start_date=model.filters_start_date,
            end_date=model.filters_end_date,
            format=ReportFormat(model.filters_format),
            form_ids=[row.form_id for row in model.filter_forms],
            operator_ids=[row.operator_id for row in model.filter_operators],
            department_ids=[row.department_id for row in model.filter_departments],
        ),
        generated_by=model.generated_by,
        status=ReportStatus(model.status),
        file_key=model.file_key,
        file_size=model.file_size,
        created_at=model.created_at,
        completed_at=model.completed_at,
    )


class SqlAlchemyReportRepository:
    """Postgres-backed implementation of `ReportRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _load_options(self):
        return (
            selectinload(ReportModel.filter_forms),
            selectinload(ReportModel.filter_operators),
            selectinload(ReportModel.filter_departments),
        )

    async def get_by_id(self, report_id: UUID) -> ReportEntity | None:
        statement = select(ReportModel).where(ReportModel.id == report_id).options(*self._load_options())
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_summary_by_id(self, report_id: UUID) -> ReportSummary | None:
        statement = (
            select(ReportModel, ProjectModel.name, UserModel.name)
            .join(ProjectModel, ProjectModel.id == ReportModel.project_id)
            .join(UserModel, UserModel.id == ReportModel.generated_by)
            .where(ReportModel.id == report_id)
            .options(*self._load_options())
        )
        result = await self._session.execute(statement)
        row = result.first()
        if row is None:
            return None
        model, project_name, generated_by_name = row
        return ReportSummary(report=_to_entity(model), project_name=project_name, generated_by_name=generated_by_name)

    async def search(
        self, query: str | None, type_: ReportType | None, project_id: UUID | None
    ) -> list[ReportSummary]:
        statement = (
            select(ReportModel, ProjectModel.name, UserModel.name)
            .join(ProjectModel, ProjectModel.id == ReportModel.project_id)
            .join(UserModel, UserModel.id == ReportModel.generated_by)
            .options(*self._load_options())
        )
        if type_ is not None:
            statement = statement.where(ReportModel.type == type_.value)
        if project_id is not None:
            statement = statement.where(ReportModel.project_id == project_id)
        if query:
            statement = statement.where(or_(ReportModel.name.ilike(f"%{query}%")))
        result = await self._session.execute(statement.order_by(ReportModel.created_at.desc()))
        return [
            ReportSummary(report=_to_entity(model), project_name=project_name, generated_by_name=generated_by_name)
            for model, project_name, generated_by_name in result.all()
        ]

    async def create(self, report: ReportEntity) -> ReportEntity:
        model = ReportModel(
            id=report.id,
            name=report.name,
            type=report.type.value,
            description=report.description,
            project_id=report.project_id,
            filters_start_date=report.filters.start_date,
            filters_end_date=report.filters.end_date,
            filters_format=report.filters.format.value,
            generated_by=report.generated_by,
            status=report.status.value,
            file_key=report.file_key,
            file_size=report.file_size,
            completed_at=report.completed_at,
            filter_forms=[ReportFilterFormModel(form_id=form_id) for form_id in report.filters.form_ids],
            filter_operators=[
                ReportFilterOperatorModel(operator_id=operator_id) for operator_id in report.filters.operator_ids
            ],
            filter_departments=[
                ReportFilterDepartmentModel(department_id=department_id)
                for department_id in report.filters.department_ids
            ],
        )
        self._session.add(model)
        await self._session.commit()
        return await self.get_by_id(model.id)  # type: ignore[return-value]

    async def update(self, report: ReportEntity) -> ReportEntity:
        model = await self._session.get(ReportModel, report.id)
        if model is None:
            raise ValueError(f"Report {report.id} not found")
        model.status = report.status.value
        model.file_key = report.file_key
        model.file_size = report.file_size
        model.completed_at = report.completed_at
        await self._session.commit()
        return await self.get_by_id(report.id)  # type: ignore[return-value]

    async def delete(self, report_id: UUID) -> None:
        model = await self._session.get(ReportModel, report_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()
