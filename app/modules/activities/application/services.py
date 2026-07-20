import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.modules.activities.application.schemas import ActivityResponse
from app.modules.activities.domain.entities import ActivityEntity, ActivityType
from app.modules.activities.domain.repositories import ActivityRepository
from app.modules.projects.domain.repositories import ProjectRepository

logger = logging.getLogger(__name__)

_DEFAULT_LIST_LIMIT = 20


class ActivityService:
    """Records what's been happening across the system for the dashboard's
    "Atividade Recente" panel. Logging is always best-effort — a failure here
    must never break the real action (attendance submitted, form published,
    etc.) that triggered it."""

    def __init__(self, repository: ActivityRepository, project_repository: ProjectRepository) -> None:
        self._repository = repository
        self._project_repository = project_repository

    async def log(
        self,
        org_id: UUID,
        type_: ActivityType,
        title: str,
        description: str,
        icon: str,
        user_id: UUID | None,
        user_name: str,
    ) -> None:
        try:
            activity = ActivityEntity(
                id=uuid.uuid4(),
                org_id=org_id,
                type=type_,
                title=title,
                description=description,
                icon=icon,
                user_id=user_id,
                user_name=user_name,
                created_at=datetime.now(timezone.utc),
            )
            await self._repository.create(activity)
        except Exception:
            logger.exception("Failed to log activity %r for org %s", title, org_id)

    async def log_for_project(
        self,
        project_id: UUID,
        type_: ActivityType,
        title: str,
        description: str,
        icon: str,
        user_id: UUID | None,
        user_name: str,
    ) -> None:
        try:
            project = await self._project_repository.get_by_id(project_id)
        except Exception:
            logger.exception("Failed to resolve org for project %s while logging activity %r", project_id, title)
            return
        if project is None:
            return
        await self.log(project.org_id, type_, title, description, icon, user_id, user_name)

    async def list_recent(self, org_id: UUID, limit: int = _DEFAULT_LIST_LIMIT) -> list[ActivityResponse]:
        activities = await self._repository.list_recent(org_id, limit)
        return [ActivityResponse.from_entity(activity) for activity in activities]
