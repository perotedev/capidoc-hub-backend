from uuid import UUID

from pydantic import BaseModel

from app.modules.operators.domain.entities import OperatorReport


class OperatorStatsResponse(BaseModel):
    today_attendances: int
    week_attendances: int
    month_attendances: int
    total_attendances: int
    avg_duration: int
    completion_rate: int


class OperatorResponse(BaseModel):
    id: UUID
    name: str
    email: str
    avatar_url: str | None
    project_id: UUID | None
    project_name: str | None
    department_id: UUID | None
    department_name: str | None
    stats: OperatorStatsResponse

    @classmethod
    def from_entity(cls, report: OperatorReport) -> "OperatorResponse":
        return cls(
            id=report.id,
            name=report.name,
            email=report.email,
            avatar_url=report.avatar_url,
            project_id=report.project_id,
            project_name=report.project_name,
            department_id=report.department_id,
            department_name=report.department_name,
            stats=OperatorStatsResponse(**vars(report.stats)),
        )
