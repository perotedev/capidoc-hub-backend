from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class NotificationType(StrEnum):
    REPORT_READY = "REPORT_READY"
    REPORT_ERROR = "REPORT_ERROR"
    DOCUMENT_READY = "DOCUMENT_READY"


@dataclass(slots=True)
class NotificationEntity:
    id: UUID
    user_id: UUID
    type: NotificationType
    title: str
    message: str
    link: str | None
    read: bool
    created_at: datetime
