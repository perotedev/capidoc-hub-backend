from pydantic import Field

from app.modules.attendances.domain.entities import GpsLocation
from app.shared.schema import CamelCaseModel


class MobileDeviceRegisterRequest(CamelCaseModel):
    """Self-service device registration — unlike the web/admin `DeviceRegisterRequest`,
    this carries no license/inventory info and always self-assigns to the caller."""

    uid: str = Field(min_length=1, max_length=200)
    model: str
    os_version: str
    app_version: str


class AttendanceResponseInput(CamelCaseModel):
    field_id: str
    field_label: str
    value: str | list[str]


class AttendancePhotoInput(CamelCaseModel):
    """Metadata for one uploaded photo/signature file, matched by list index to
    the `photo_files` part of the multipart request."""

    field_id: str
    caption: str = ""


class AttendanceSubmitRequest(CamelCaseModel):
    form_id: str
    duration: int = 0
    responses: list[AttendanceResponseInput] = Field(default_factory=list)
    photos: list[AttendancePhotoInput] = Field(default_factory=list)
    gps_location: GpsLocation | None = None
