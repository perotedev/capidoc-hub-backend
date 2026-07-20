from datetime import datetime

from app.shared.schema import CamelCaseModel


class GpsPoint(CamelCaseModel):
    latitude: float
    longitude: float
    accuracy: float
    timestamp: datetime


class JourneyEntity(CamelCaseModel):
    """One operator's workday — the Android app reports start/end (each with a
    selfie + GPS fix) so the web can show a "day detail" timeline. Document-shaped
    (like forms/attendances), keyed by operator_id + date."""

    id: str
    operator_id: str
    project_id: str
    date: str  # YYYY-MM-DD, operator-local calendar day
    start_photo_file_key: str | None = None
    start_gps: GpsPoint | None = None
    started_at: datetime | None = None
    end_photo_file_key: str | None = None
    end_gps: GpsPoint | None = None
    ended_at: datetime | None = None


class LocationPingEntity(CamelCaseModel):
    """A single GPS breadcrumb reported while a journey is active."""

    id: str
    operator_id: str
    project_id: str
    date: str  # YYYY-MM-DD, denormalized from point.timestamp for simple day queries
    point: GpsPoint
