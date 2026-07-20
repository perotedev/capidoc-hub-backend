from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.activities.domain.entities import ActivityEntity, ActivityType
from app.modules.activities.infrastructure.models import ActivityModel


def _to_entity(model: ActivityModel) -> ActivityEntity:
    return ActivityEntity(
        id=model.id,
        org_id=model.org_id,
        type=ActivityType(model.type),
        title=model.title,
        description=model.description,
        icon=model.icon,
        user_id=model.user_id,
        user_name=model.user_name,
        created_at=model.created_at,
    )


class SqlAlchemyActivityRepository:
    """Postgres-backed implementation of `ActivityRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, activity: ActivityEntity) -> ActivityEntity:
        model = ActivityModel(
            id=activity.id,
            org_id=activity.org_id,
            type=activity.type.value,
            title=activity.title,
            description=activity.description,
            icon=activity.icon,
            user_id=activity.user_id,
            user_name=activity.user_name,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_recent(self, org_id: UUID, limit: int) -> list[ActivityEntity]:
        statement = (
            select(ActivityModel)
            .where(ActivityModel.org_id == org_id)
            .order_by(ActivityModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return [_to_entity(model) for model in result.scalars().all()]
