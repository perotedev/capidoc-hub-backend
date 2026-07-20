from datetime import datetime

from pydantic import BaseModel, Field


class GpsLocation(BaseModel):
    latitude: float
    longitude: float
    accuracy: float


class AttendanceResponse(BaseModel):
    field_id: str
    field_label: str
    value: str | list[str]


class AttendancePhoto(BaseModel):
    id: str
    caption: str = ""
    file_key: str


class AttendanceEntity(BaseModel):
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


class AttendanceStats(BaseModel):
    total: int
    today: int
    this_week: int
    avg_duration: int
    by_day: list[dict]
