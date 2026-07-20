from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.notifications.application.services import NotificationService
from app.modules.notifications.domain.repositories import NotificationRepository
from app.modules.notifications.infrastructure.repository import SqlAlchemyNotificationRepository


def get_notification_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> NotificationRepository:
    return SqlAlchemyNotificationRepository(session)


def get_notification_service(
    repository: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> NotificationService:
    return NotificationService(repository)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
