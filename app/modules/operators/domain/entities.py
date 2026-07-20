from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class OperatorStats:
    today_attendances: int
    week_attendances: int
    month_attendances: int
    total_attendances: int
    avg_duration: int
    completion_rate: int


@dataclass(slots=True)
class OperatorReport:
    id: UUID
    name: str
    email: str
    avatar_url: str | None
    project_id: UUID | None
    project_name: str | None
    department_id: UUID | None
    department_name: str | None
    stats: OperatorStats
