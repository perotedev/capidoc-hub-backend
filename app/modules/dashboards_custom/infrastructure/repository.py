from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.dashboards_custom.domain.entities import (
    DashboardCustomEntity,
    DashboardCustomSummary,
    DashboardWidgetEntity,
    WidgetConfig,
    WidgetPosition,
    WidgetType,
)
from app.modules.dashboards_custom.infrastructure.models import (
    DashboardCustomModel,
    DashboardShareModel,
    DashboardWidgetModel,
)
from app.modules.projects.infrastructure.models import ProjectModel
from app.modules.users.infrastructure.models import UserModel


def _widget_to_entity(model: DashboardWidgetModel) -> DashboardWidgetEntity:
    return DashboardWidgetEntity(
        id=model.id,
        type=WidgetType(model.type),
        title=model.title,
        config=WidgetConfig(**model.config),
        position=WidgetPosition(
            x=model.position_x, y=model.position_y, cols=model.position_cols, rows=model.position_rows
        ),
    )


def _to_entity(model: DashboardCustomModel) -> DashboardCustomEntity:
    return DashboardCustomEntity(
        id=model.id,
        name=model.name,
        description=model.description,
        project_id=model.project_id,
        created_by=model.created_by,
        widgets=[_widget_to_entity(widget) for widget in model.widgets],
        shared=model.shared,
        shared_with=[share.user_id for share in model.shares],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyDashboardCustomRepository:
    """Postgres-backed implementation of `DashboardCustomRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _load_options(self):
        return (selectinload(DashboardCustomModel.widgets), selectinload(DashboardCustomModel.shares))

    async def get_by_id(self, dashboard_id: UUID) -> DashboardCustomEntity | None:
        statement = (
            select(DashboardCustomModel)
            .where(DashboardCustomModel.id == dashboard_id)
            .options(*self._load_options())
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_summary_by_id(self, dashboard_id: UUID) -> DashboardCustomSummary | None:
        statement = (
            select(DashboardCustomModel, ProjectModel.name, UserModel.name)
            .join(ProjectModel, ProjectModel.id == DashboardCustomModel.project_id)
            .join(UserModel, UserModel.id == DashboardCustomModel.created_by)
            .where(DashboardCustomModel.id == dashboard_id)
            .options(*self._load_options())
        )
        result = await self._session.execute(statement)
        row = result.first()
        if row is None:
            return None
        model, project_name, created_by_name = row
        return DashboardCustomSummary(dashboard=_to_entity(model), project_name=project_name, created_by_name=created_by_name)

    async def list_accessible_to(self, user_id: UUID, project_id: UUID | None) -> list[DashboardCustomSummary]:
        statement = (
            select(DashboardCustomModel, ProjectModel.name, UserModel.name)
            .join(ProjectModel, ProjectModel.id == DashboardCustomModel.project_id)
            .join(UserModel, UserModel.id == DashboardCustomModel.created_by)
            .outerjoin(DashboardShareModel, DashboardShareModel.dashboard_id == DashboardCustomModel.id)
            .where(
                or_(
                    DashboardCustomModel.created_by == user_id,
                    DashboardShareModel.user_id == user_id,
                )
            )
            .options(*self._load_options())
        )
        if project_id is not None:
            statement = statement.where(DashboardCustomModel.project_id == project_id)
        result = await self._session.execute(statement.order_by(DashboardCustomModel.name).distinct())
        return [
            DashboardCustomSummary(dashboard=_to_entity(model), project_name=project_name, created_by_name=created_by_name)
            for model, project_name, created_by_name in result.unique().all()
        ]

    async def create(self, dashboard: DashboardCustomEntity) -> DashboardCustomEntity:
        model = DashboardCustomModel(
            id=dashboard.id,
            name=dashboard.name,
            description=dashboard.description,
            project_id=dashboard.project_id,
            created_by=dashboard.created_by,
            shared=dashboard.shared,
        )
        self._session.add(model)
        await self._session.commit()
        return await self.get_by_id(model.id)  # type: ignore[return-value]

    async def update(self, dashboard: DashboardCustomEntity) -> DashboardCustomEntity:
        model = await self._session.get(
            DashboardCustomModel, dashboard.id, options=[*self._load_options()]
        )
        if model is None:
            raise ValueError(f"Dashboard {dashboard.id} not found")

        model.name = dashboard.name
        model.description = dashboard.description
        model.shared = dashboard.shared

        model.widgets = [
            DashboardWidgetModel(
                id=widget.id,
                type=widget.type.value,
                title=widget.title,
                config=vars(widget.config),
                position_x=widget.position.x,
                position_y=widget.position.y,
                position_cols=widget.position.cols,
                position_rows=widget.position.rows,
            )
            for widget in dashboard.widgets
        ]
        model.shares = [DashboardShareModel(user_id=user_id) for user_id in dashboard.shared_with]

        await self._session.commit()
        return await self.get_by_id(dashboard.id)  # type: ignore[return-value]

    async def delete(self, dashboard_id: UUID) -> None:
        model = await self._session.get(DashboardCustomModel, dashboard_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()
