from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.domain.entities import NotificationEntity, NotificationType
from app.modules.notifications.infrastructure.models import NotificationModel


def _to_entity(model: NotificationModel) -> NotificationEntity:
    return NotificationEntity(
        id=model.id,
        user_id=model.user_id,
        type=NotificationType(model.type),
        title=model.title,
        message=model.message,
        link=model.link,
        read=model.read,
        created_at=model.created_at,
    )


class SqlAlchemyNotificationRepository:
    """Postgres-backed implementation of `NotificationRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, notification: NotificationEntity) -> NotificationEntity:
        model = NotificationModel(
            id=notification.id,
            user_id=notification.user_id,
            type=notification.type.value,
            title=notification.title,
            message=notification.message,
            link=notification.link,
            read=notification.read,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_for_user(self, user_id: UUID, unread_only: bool, limit: int) -> list[NotificationEntity]:
        statement = select(NotificationModel).where(NotificationModel.user_id == user_id)
        if unread_only:
            statement = statement.where(NotificationModel.read.is_(False))
        statement = statement.order_by(NotificationModel.created_at.desc()).limit(limit)
        result = await self._session.execute(statement)
        return [_to_entity(model) for model in result.scalars().all()]

    async def count_unread(self, user_id: UUID) -> int:
        statement = select(func.count()).select_from(NotificationModel).where(
            NotificationModel.user_id == user_id, NotificationModel.read.is_(False)
        )
        result = await self._session.execute(statement)
        return result.scalar_one()

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> None:
        statement = (
            update(NotificationModel)
            .where(NotificationModel.id == notification_id, NotificationModel.user_id == user_id)
            .values(read=True)
        )
        await self._session.execute(statement)
        await self._session.commit()

    async def mark_all_read(self, user_id: UUID) -> None:
        statement = (
            update(NotificationModel)
            .where(NotificationModel.user_id == user_id, NotificationModel.read.is_(False))
            .values(read=True)
        )
        await self._session.execute(statement)
        await self._session.commit()
