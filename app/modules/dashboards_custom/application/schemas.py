from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.dashboards_custom.domain.entities import DashboardCustomSummary, WidgetType


class WidgetConfigSchema(BaseModel):
    data_source: str
    filters: dict[str, str] = Field(default_factory=dict)
    period: str = ""
    color: str = ""
    show_legend: bool = True
    refresh_interval: int | None = None
    custom_options: dict[str, Any] = Field(default_factory=dict)


class WidgetPositionSchema(BaseModel):
    x: int
    y: int
    cols: int
    rows: int


class DashboardWidgetSchema(BaseModel):
    id: UUID | None = None
    type: WidgetType
    title: str
    config: WidgetConfigSchema
    position: WidgetPositionSchema


class DashboardCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    project_id: UUID


class DashboardUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    widgets: list[DashboardWidgetSchema] | None = None
    shared: bool | None = None
    shared_with: list[UUID] | None = None


class AddWidgetRequest(BaseModel):
    type: WidgetType
    title: str


class DashboardResponse(BaseModel):
    id: UUID
    name: str
    description: str
    project_id: UUID
    project_name: str
    created_by: UUID
    created_by_name: str
    widgets: list[DashboardWidgetSchema]
    shared: bool
    shared_with: list[UUID]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_summary(cls, summary: DashboardCustomSummary) -> "DashboardResponse":
        dashboard = summary.dashboard
        return cls(
            id=dashboard.id,
            name=dashboard.name,
            description=dashboard.description,
            project_id=dashboard.project_id,
            project_name=summary.project_name,
            created_by=dashboard.created_by,
            created_by_name=summary.created_by_name,
            widgets=[
                DashboardWidgetSchema(
                    id=widget.id,
                    type=widget.type,
                    title=widget.title,
                    config=WidgetConfigSchema(**vars(widget.config)),
                    position=WidgetPositionSchema(**vars(widget.position)),
                )
                for widget in dashboard.widgets
            ],
            shared=dashboard.shared,
            shared_with=dashboard.shared_with,
            created_at=dashboard.created_at,
            updated_at=dashboard.updated_at,
        )
