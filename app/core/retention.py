"""Periodic data retention cleanup — deletes old `activities` and old *read*
`notifications` rows so those tables don't grow forever. Runs as a background
asyncio task started from the app's lifespan (see `app/main.py`); no external
scheduler (cron, Celery, etc.) is needed for a job this simple.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.modules.activities.infrastructure.models import ActivityModel
from app.modules.notifications.infrastructure.models import NotificationModel

logger = logging.getLogger(__name__)
settings = get_settings()


async def cleanup_old_activities() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.activity_retention_days)
    async with async_session_factory() as session:
        result = await session.execute(delete(ActivityModel).where(ActivityModel.created_at < cutoff))
        await session.commit()
        return result.rowcount or 0


async def cleanup_old_notifications() -> int:
    """Only ever deletes *read* notifications — an old unread one still needs
    the user's attention, so it's kept regardless of age."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.notification_retention_days)
    async with async_session_factory() as session:
        result = await session.execute(
            delete(NotificationModel).where(NotificationModel.read.is_(True), NotificationModel.created_at < cutoff)
        )
        await session.commit()
        return result.rowcount or 0


async def run_retention_cleanup() -> None:
    try:
        activities_deleted = await cleanup_old_activities()
        notifications_deleted = await cleanup_old_notifications()
        if activities_deleted or notifications_deleted:
            logger.info(
                "Retention cleanup: removed %d old activities, %d old read notifications",
                activities_deleted,
                notifications_deleted,
            )
    except Exception:
        logger.exception("Retention cleanup failed")


async def retention_cleanup_loop() -> None:
    """Runs until cancelled at shutdown, sleeping between passes."""
    interval_seconds = settings.retention_cleanup_interval_hours * 3600
    while True:
        await run_retention_cleanup()
        await asyncio.sleep(interval_seconds)
