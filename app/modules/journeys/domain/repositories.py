from typing import Protocol

from app.modules.journeys.domain.entities import JourneyEntity, LocationPingEntity


class JourneyRepository(Protocol):
    async def get_by_operator_and_date(self, operator_id: str, date: str) -> JourneyEntity | None: ...

    async def upsert(self, journey: JourneyEntity) -> JourneyEntity: ...


class LocationPingRepository(Protocol):
    async def create_many(self, pings: list[LocationPingEntity]) -> None: ...

    async def list_for_operator_date(self, operator_id: str, date: str) -> list[LocationPingEntity]: ...
