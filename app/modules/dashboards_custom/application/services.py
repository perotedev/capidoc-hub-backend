import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.dashboards_custom.application.schemas import (
    AddWidgetRequest,
    DashboardCreateRequest,
    DashboardResponse,
    DashboardUpdateRequest,
)
from app.modules.dashboards_custom.domain.entities import (
    DashboardCustomEntity,
    DashboardCustomSummary,
    DashboardWidgetEntity,
    WidgetConfig,
    WidgetPosition,
)
from app.modules.dashboards_custom.domain.repositories import DashboardCustomRepository


def _can_access(summary: DashboardCustomSummary, user_id: UUID) -> bool:
    dashboard = summary.dashboard
    return dashboard.created_by == user_id or dashboard.shared or user_id in dashboard.shared_with


class DashboardCustomService:
    def __init__(self, repository: DashboardCustomRepository) -> None:
        self._repository = repository

    async def _get_summary(self, dashboard_id: UUID) -> DashboardCustomSummary:
        summary = await self._repository.get_summary_by_id(dashboard_id)
        if summary is None:
            raise NotFoundError(f"Dashboard {dashboard_id} not found")
        return summary

    async def get_dashboard(self, dashboard_id: UUID, current_user_id: UUID) -> DashboardResponse:
        summary = await self._get_summary(dashboard_id)
        if not _can_access(summary, current_user_id):
            raise ForbiddenError("You do not have access to this dashboard")
        return DashboardResponse.from_summary(summary)

    async def list_accessible(self, current_user_id: UUID, project_id: UUID | None) -> list[DashboardResponse]:
        summaries = await self._repository.list_accessible_to(current_user_id, project_id)
        return [DashboardResponse.from_summary(summary) for summary in summaries]

    async def create_dashboard(self, request: DashboardCreateRequest, created_by: UUID) -> DashboardResponse:
        now = datetime.now(timezone.utc)
        dashboard = DashboardCustomEntity(
            id=uuid.uuid4(),
            name=request.name,
            description=request.description,
            project_id=request.project_id,
            created_by=created_by,
            widgets=[],
            shared=False,
            shared_with=[],
            created_at=now,
            updated_at=now,
        )
        created = await self._repository.create(dashboard)
        return await self.get_dashboard(created.id, created_by)

    async def _require_owner(self, dashboard_id: UUID, current_user_id: UUID) -> DashboardCustomSummary:
        summary = await self._get_summary(dashboard_id)
        if summary.dashboard.created_by != current_user_id:
            raise ForbiddenError("Only the dashboard's owner can modify it")
        return summary

    async def update_dashboard(
        self, dashboard_id: UUID, request: DashboardUpdateRequest, current_user_id: UUID
    ) -> DashboardResponse:
        summary = await self._require_owner(dashboard_id, current_user_id)
        dashboard = summary.dashboard

        if request.name is not None:
            dashboard.name = request.name
        if request.description is not None:
            dashboard.description = request.description
        if request.shared is not None:
            dashboard.shared = request.shared
        if request.shared_with is not None:
            dashboard.shared_with = request.shared_with
        if request.widgets is not None:
            dashboard.widgets = [
                DashboardWidgetEntity(
                    id=widget.id or uuid.uuid4(),
                    type=widget.type,
                    title=widget.title,
                    config=WidgetConfig(**widget.config.model_dump()),
                    position=WidgetPosition(**widget.position.model_dump()),
                )
                for widget in request.widgets
            ]

        await self._repository.update(dashboard)
        return await self.get_dashboard(dashboard_id, current_user_id)

    async def add_widget(
        self, dashboard_id: UUID, request: AddWidgetRequest, current_user_id: UUID
    ) -> DashboardResponse:
        summary = await self._require_owner(dashboard_id, current_user_id)
        dashboard = summary.dashboard
        dashboard.widgets.append(
            DashboardWidgetEntity(
                id=uuid.uuid4(),
                type=request.type,
                title=request.title,
                config=WidgetConfig(data_source=""),
                position=WidgetPosition(x=0, y=0, cols=4, rows=2),
            )
        )
        await self._repository.update(dashboard)
        return await self.get_dashboard(dashboard_id, current_user_id)

    async def remove_widget(self, dashboard_id: UUID, widget_id: UUID, current_user_id: UUID) -> DashboardResponse:
        summary = await self._require_owner(dashboard_id, current_user_id)
        dashboard = summary.dashboard
        dashboard.widgets = [widget for widget in dashboard.widgets if widget.id != widget_id]
        await self._repository.update(dashboard)
        return await self.get_dashboard(dashboard_id, current_user_id)

    async def delete_dashboard(self, dashboard_id: UUID, current_user_id: UUID) -> None:
        await self._require_owner(dashboard_id, current_user_id)
        await self._repository.delete(dashboard_id)
