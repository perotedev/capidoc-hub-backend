from typing import Annotated

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.core.cache import FileUrlCacheServiceDep
from app.core.mongodb import get_mongo_db
from app.modules.attendances.application.services import AttendanceService
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.attendances.infrastructure.mongo_repository import MongoAttendanceRepository


def get_attendance_repository(
    database: Annotated[AsyncDatabase, Depends(get_mongo_db)],
) -> AttendanceRepository:
    return MongoAttendanceRepository(database)


def get_attendance_service(
    repository: Annotated[AttendanceRepository, Depends(get_attendance_repository)],
    file_url_cache: FileUrlCacheServiceDep,
) -> AttendanceService:
    return AttendanceService(repository, file_url_cache)


AttendanceServiceDep = Annotated[AttendanceService, Depends(get_attendance_service)]
