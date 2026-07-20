from typing import Protocol
from uuid import UUID

from app.modules.activities.domain.entities import ActivityEntity


class ActivityRepository(Protocol):
    async def create(self, activity: ActivityEntity) -> ActivityEntity: ...

    async def list_recent(self, org_id: UUID, limit: int) -> list[ActivityEntity]: ...
