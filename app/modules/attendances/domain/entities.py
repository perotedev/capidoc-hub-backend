from datetime import datetime

from pydantic import Field

from app.shared.schema import CamelCaseModel


class GpsLocation(CamelCaseModel):
    latitude: float
    longitude: float
    accuracy: float


class AttendanceResponse(CamelCaseModel):
    field_id: str
    field_label: str
    value: str | list[str]


class AttendancePhoto(CamelCaseModel):
    id: str
    field_id: str | None = None
    caption: str = ""
    file_key: str


class AttendanceEntity(CamelCaseModel):
    """Domain representation of a submitted form response (an "attendance").

    Like forms, attendances are document-shaped — their `responses` mirror
    whatever fields the originating form defined — so this model doubles as
    both the domain entity and the MongoDB document schema.
    """

    id: str
    form_id: str
    form_name: str
    operator_id: str
    operator_name: str
    project_id: str
    project_name: str
    duration: int = 0
    responses: list[AttendanceResponse] = Field(default_factory=list)
    photos: list[AttendancePhoto] = Field(default_factory=list)
    signature: bool = False
    gps_location: GpsLocation | None = None
    created_at: datetime
    completed_at: datetime
    synced_at: datetime | None = None


class AttendanceStats(CamelCaseModel):
    total: int
    today: int
    yesterday: int
    this_week: int
    last_week: int
    avg_duration: int
    by_day: list[dict]
