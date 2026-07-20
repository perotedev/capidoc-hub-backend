from pymongo.asynchronous.database import AsyncDatabase

from app.modules.journeys.domain.entities import JourneyEntity, LocationPingEntity

_JOURNEYS_COLLECTION = "journeys"
_LOCATION_PINGS_COLLECTION = "location_pings"


def _journey_to_entity(document: dict) -> JourneyEntity:
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return JourneyEntity.model_validate(document)


def _journey_to_document(journey: JourneyEntity) -> dict:
    return journey.model_dump(exclude={"id"}, mode="json")


def _ping_to_entity(document: dict) -> LocationPingEntity:
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return LocationPingEntity.model_validate(document)


def _ping_to_document(ping: LocationPingEntity) -> dict:
    return ping.model_dump(exclude={"id"}, mode="json")


class MongoJourneyRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._collection = database[_JOURNEYS_COLLECTION]

    async def get_by_operator_and_date(self, operator_id: str, date: str) -> JourneyEntity | None:
        document = await self._collection.find_one({"operator_id": operator_id, "date": date})
        return _journey_to_entity(document) if document else None

    async def upsert(self, journey: JourneyEntity) -> JourneyEntity:
        document = _journey_to_document(journey)
        await self._collection.update_one(
            {"operator_id": journey.operator_id, "date": journey.date},
            {"$set": document},
            upsert=True,
        )
        saved = await self._collection.find_one({"operator_id": journey.operator_id, "date": journey.date})
        return _journey_to_entity(saved)


class MongoLocationPingRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._collection = database[_LOCATION_PINGS_COLLECTION]

    async def create_many(self, pings: list[LocationPingEntity]) -> None:
        if not pings:
            return
        await self._collection.insert_many([_ping_to_document(ping) for ping in pings])

    async def list_for_operator_date(self, operator_id: str, date: str) -> list[LocationPingEntity]:
        cursor = self._collection.find({"operator_id": operator_id, "date": date}).sort("point.timestamp", 1)
        documents = await cursor.to_list(length=None)
        return [_ping_to_entity(document) for document in documents]
