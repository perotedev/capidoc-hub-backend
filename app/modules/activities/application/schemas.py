from datetime import datetime
from uuid import UUID

from app.modules.activities.domain.entities import ActivityEntity, ActivityType
from app.shared.schema import CamelCaseModel


class ActivityResponse(CamelCaseModel):
    id: UUID
    type: ActivityType
    title: str
    description: str
    icon: str
    user_id: UUID | None
    user_name: str
    # The frontend's `ActivityItem` interface names this `timestamp`, not
    # `createdAt` — matched explicitly here rather than renaming the domain
    # entity's field to keep `created_at` consistent with every other module.
    timestamp: datetime

    @classmethod
    def from_entity(cls, entity: ActivityEntity) -> "ActivityResponse":
        return cls(
            id=entity.id,
            type=entity.type,
            title=entity.title,
            description=entity.description,
            icon=entity.icon,
            user_id=entity.user_id,
            user_name=entity.user_name,
            timestamp=entity.created_at,
        )
