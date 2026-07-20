from typing import Annotated

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.core.mongodb import get_mongo_db
from app.core.storage import StorageService, get_storage_service
from app.modules.forms.application.services import FormService
from app.modules.forms.domain.repositories import FormRepository
from app.modules.forms.infrastructure.mongo_repository import MongoFormRepository


def get_form_repository(database: Annotated[AsyncDatabase, Depends(get_mongo_db)]) -> FormRepository:
    return MongoFormRepository(database)


def get_form_service(
    repository: Annotated[FormRepository, Depends(get_form_repository)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> FormService:
    return FormService(repository, storage)


FormServiceDep = Annotated[FormService, Depends(get_form_service)]
