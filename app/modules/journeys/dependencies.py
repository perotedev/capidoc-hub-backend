from typing import Annotated

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.core.mongodb import get_mongo_db
from app.modules.journeys.domain.repositories import JourneyRepository, LocationPingRepository
from app.modules.journeys.infrastructure.mongo_repository import MongoJourneyRepository, MongoLocationPingRepository


def get_journey_repository(database: Annotated[AsyncDatabase, Depends(get_mongo_db)]) -> JourneyRepository:
    return MongoJourneyRepository(database)


def get_location_ping_repository(
    database: Annotated[AsyncDatabase, Depends(get_mongo_db)],
) -> LocationPingRepository:
    return MongoLocationPingRepository(database)


JourneyRepositoryDep = Annotated[JourneyRepository, Depends(get_journey_repository)]
LocationPingRepositoryDep = Annotated[LocationPingRepository, Depends(get_location_ping_repository)]
