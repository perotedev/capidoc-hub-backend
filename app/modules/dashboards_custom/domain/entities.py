from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class WidgetType(StrEnum):
    KPI = "KPI"
    LINE_CHART = "LINE_CHART"
    BAR_CHART = "BAR_CHART"
    PIE_CHART = "PIE_CHART"
    DOUGHNUT_CHART = "DOUGHNUT_CHART"
    TABLE = "TABLE"
    MAP = "MAP"
    ACTIVITY_FEED = "ACTIVITY_FEED"


@dataclass(slots=True)
class WidgetPosition:
    x: int
    y: int
    cols: int
    rows: int


@dataclass(slots=True)
class WidgetConfig:
    """Free-form per-widget settings — stored as JSONB since its shape varies by
    `WidgetType` and is owned entirely by the frontend widget renderer."""

    data_source: str
    filters: dict[str, str] = field(default_factory=dict)
    period: str = ""
    color: str = ""
    show_legend: bool = True
    refresh_interval: int | None = None
    custom_options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DashboardWidgetEntity:
    id: UUID
    type: WidgetType
    title: str
    config: WidgetConfig
    position: WidgetPosition


@dataclass(slots=True)
class DashboardCustomEntity:
    id: UUID
    name: str
    description: str
    project_id: UUID
    created_by: UUID
    widgets: list[DashboardWidgetEntity]
    shared: bool
    shared_with: list[UUID]
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class DashboardCustomSummary:
    dashboard: DashboardCustomEntity
    project_name: str
    created_by_name: str
