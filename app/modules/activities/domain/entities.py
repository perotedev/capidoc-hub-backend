from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ActivityType(StrEnum):
    ATTENDANCE = "attendance"
    DOCUMENT = "document"
    FORM = "form"
    USER = "user"
    SYSTEM = "system"


@dataclass(slots=True)
class ActivityEntity:
    id: UUID
    org_id: UUID
    type: ActivityType
    title: str
    description: str
    icon: str
    user_id: UUID | None
    user_name: str
    created_at: datetime
