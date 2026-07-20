from datetime import datetime, timezone

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from app.modules.forms.domain.entities import FormEntity, FormField, FormSettings, FormStatus, TemplateBox

_COLLECTION_NAME = "forms"


def _to_entity(document: dict) -> FormEntity:
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return FormEntity.model_validate(document)


def _to_document(form: FormEntity) -> dict:
    document = form.model_dump(exclude={"id"}, mode="json")
    return document


class MongoFormRepository:
    """MongoDB-backed implementation of `FormRepository`."""

    def __init__(self, database: AsyncDatabase) -> None:
        self._collection = database[_COLLECTION_NAME]

    async def get_by_id(self, form_id: str) -> FormEntity | None:
        document = await self._collection.find_one({"_id": ObjectId(form_id)})
        return _to_entity(document) if document else None

    async def search(
        self, query: str | None, status: FormStatus | None, project_id: str | None
    ) -> list[FormEntity]:
        mongo_filter: dict = {}
        if status is not None:
            mongo_filter["status"] = status.value
        if project_id is not None:
            mongo_filter["project_id"] = project_id
        if query:
            mongo_filter["$or"] = [
                {"name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
            ]

        cursor = self._collection.find(mongo_filter).sort("created_at", -1)
        documents = await cursor.to_list(length=None)
        return [_to_entity(document) for document in documents]

    async def create(self, form: FormEntity) -> FormEntity:
        document = _to_document(form)
        result = await self._collection.insert_one(document)
        created = await self._collection.find_one({"_id": result.inserted_id})
        return _to_entity(created)

    async def update_fields(self, form_id: str, fields: list[FormField]) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(form_id)},
            {
                "$set": {
                    "fields": [field.model_dump(mode="json") for field in fields],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    async def update_settings(self, form_id: str, settings: FormSettings) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(form_id)},
            {
                "$set": {
                    "settings": settings.model_dump(mode="json"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    async def update_template(self, form_id: str, template: list[TemplateBox]) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(form_id)},
            {
                "$set": {
                    "template": [box.model_dump(mode="json") for box in template],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    async def update_template_pdf(self, form_id: str, file_key: str | None) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(form_id)},
            {
                "$set": {
                    "template_pdf_file_key": file_key,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    async def rename(self, form_id: str, name: str, description: str) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(form_id)},
            {
                "$set": {
                    "name": name,
                    "description": description,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    async def set_status(self, form_id: str, status: FormStatus) -> None:
        update: dict = {"status": status.value, "updated_at": datetime.now(timezone.utc).isoformat()}
        if status == FormStatus.PUBLISHED:
            update["published_at"] = datetime.now(timezone.utc).isoformat()
        await self._collection.update_one({"_id": ObjectId(form_id)}, {"$set": update})

    async def increment_attendances_count(self, form_id: str) -> None:
        await self._collection.update_one({"_id": ObjectId(form_id)}, {"$inc": {"attendances_count": 1}})

    async def delete(self, form_id: str) -> None:
        await self._collection.delete_one({"_id": ObjectId(form_id)})
