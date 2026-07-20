import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.modules.notifications.application.schemas import NotificationResponse
from app.modules.notifications.domain.entities import NotificationEntity, NotificationType
from app.modules.notifications.domain.repositories import NotificationRepository

_DEFAULT_LIST_LIMIT = 50


class NotificationService:
    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    async def notify(
        self, user_id: UUID, type_: NotificationType, title: str, message: str, link: str | None = None
    ) -> NotificationResponse:
        notification = NotificationEntity(
            id=uuid.uuid4(),
            user_id=user_id,
            type=type_,
            title=title,
            message=message,
            link=link,
            read=False,
            created_at=datetime.now(timezone.utc),
        )
        created = await self._repository.create(notification)
        return NotificationResponse.from_entity(created)

    async def list_for_user(self, user_id: UUID, unread_only: bool) -> list[NotificationResponse]:
        notifications = await self._repository.list_for_user(user_id, unread_only, _DEFAULT_LIST_LIMIT)
        return [NotificationResponse.from_entity(notification) for notification in notifications]

    async def count_unread(self, user_id: UUID) -> int:
        return await self._repository.count_unread(user_id)

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> None:
        await self._repository.mark_read(notification_id, user_id)

    async def mark_all_read(self, user_id: UUID) -> None:
        await self._repository.mark_all_read(user_id)
