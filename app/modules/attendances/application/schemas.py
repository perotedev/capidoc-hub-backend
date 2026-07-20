from datetime import datetime

from pydantic import BaseModel

from app.modules.attendances.domain.entities import AttendanceResponse, GpsLocation


class AttendancePhotoResponse(BaseModel):
    id: str
    caption: str
    url: str


class AttendanceDetailResponse(BaseModel):
    """API response for an attendance — like `AttendanceEntity`, but with each
    photo's S3 key resolved to a temporary signed URL (cached in Redis)."""

    id: str
    form_id: str
    form_name: str
    operator_id: str
    operator_name: str
    project_id: str
    project_name: str
    duration: int
    responses: list[AttendanceResponse]
    photos: list[AttendancePhotoResponse]
    signature: bool
    gps_location: GpsLocation | None
    created_at: datetime
    completed_at: datetime
    synced_at: datetime | None


class AttendanceStatsResponse(BaseModel):
    total: int
    today: int
    this_week: int
    avg_duration: int
    by_day: list[dict]
