from datetime import datetime
from uuid import UUID

from app.modules.notifications.domain.entities import NotificationEntity, NotificationType
from app.shared.schema import CamelCaseModel


class NotificationResponse(CamelCaseModel):
    id: UUID
    type: NotificationType
    title: str
    message: str
    link: str | None
    read: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: NotificationEntity) -> "NotificationResponse":
        return cls(
            id=entity.id,
            type=entity.type,
            title=entity.title,
            message=entity.message,
            link=entity.link,
            read=entity.read,
            created_at=entity.created_at,
        )


class UnreadCountResponse(CamelCaseModel):
    count: int
