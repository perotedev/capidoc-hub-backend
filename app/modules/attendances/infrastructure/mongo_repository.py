from collections import Counter
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from app.modules.attendances.domain.entities import AttendanceEntity, AttendanceStats

_COLLECTION_NAME = "attendances"


def _to_entity(document: dict) -> AttendanceEntity:
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return AttendanceEntity.model_validate(document)


def _to_document(attendance: AttendanceEntity) -> dict:
    return attendance.model_dump(exclude={"id"}, mode="json")


class MongoAttendanceRepository:
    """MongoDB-backed implementation of `AttendanceRepository`."""

    def __init__(self, database: AsyncDatabase) -> None:
        self._collection = database[_COLLECTION_NAME]

    async def get_by_id(self, attendance_id: str) -> AttendanceEntity | None:
        document = await self._collection.find_one({"_id": ObjectId(attendance_id)})
        return _to_entity(document) if document else None

    async def search(self, query: str | None, form_id: str | None) -> list[AttendanceEntity]:
        mongo_filter: dict = {}
        if form_id:
            mongo_filter["form_id"] = form_id
        if query:
            mongo_filter["$or"] = [
                {"operator_name": {"$regex": query, "$options": "i"}},
                {"form_name": {"$regex": query, "$options": "i"}},
            ]
        cursor = self._collection.find(mongo_filter).sort("created_at", -1)
        documents = await cursor.to_list(length=None)
        return [_to_entity(document) for document in documents]

    async def search_by_form(
        self,
        form_id: str,
        query: str | None,
        start_date: str | None,
        end_date: str | None,
        field_id: str | None,
        field_value: str | None,
    ) -> list[AttendanceEntity]:
        mongo_filter: dict = {"form_id": form_id}
        if query:
            mongo_filter["operator_name"] = {"$regex": query, "$options": "i"}
        if start_date or end_date:
            date_filter: dict = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = f"{end_date}T23:59:59Z"
            mongo_filter["created_at"] = date_filter
        if field_id and field_value:
            mongo_filter["responses"] = {
                "$elemMatch": {"field_id": field_id, "value": {"$regex": field_value, "$options": "i"}}
            }

        cursor = self._collection.find(mongo_filter).sort("created_at", -1)
        documents = await cursor.to_list(length=None)
        return [_to_entity(document) for document in documents]

    async def get_stats(self, project_id: str | None) -> AttendanceStats:
        mongo_filter: dict = {}
        if project_id:
            mongo_filter["project_id"] = project_id

        cursor = self._collection.find(mongo_filter)
        documents = await cursor.to_list(length=None)
        attendances = [_to_entity(document) for document in documents]

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=today_start.weekday())
        last_week_start = week_start - timedelta(days=7)

        today_count = sum(1 for a in attendances if a.created_at >= today_start)
        yesterday_count = sum(1 for a in attendances if yesterday_start <= a.created_at < today_start)
        week_count = sum(1 for a in attendances if a.created_at >= week_start)
        last_week_count = sum(1 for a in attendances if last_week_start <= a.created_at < week_start)
        avg_duration = int(sum(a.duration for a in attendances) / len(attendances)) if attendances else 0

        by_day_counter: Counter[str] = Counter()
        for attendance in attendances:
            if attendance.created_at >= now - timedelta(days=7):
                by_day_counter[attendance.created_at.strftime("%Y-%m-%d")] += 1

        by_day = [{"date": date, "count": count} for date, count in sorted(by_day_counter.items())]

        return AttendanceStats(
            total=len(attendances),
            today=today_count,
            yesterday=yesterday_count,
            this_week=week_count,
            last_week=last_week_count,
            avg_duration=avg_duration,
            by_day=by_day,
        )

    async def search_for_report(
        self,
        project_id: str,
        start_date: str | None,
        end_date: str | None,
        form_ids: list[str],
        operator_ids: list[str],
    ) -> list[AttendanceEntity]:
        mongo_filter: dict = {"project_id": project_id}
        if form_ids:
            mongo_filter["form_id"] = {"$in": form_ids}
        if operator_ids:
            mongo_filter["operator_id"] = {"$in": operator_ids}
        if start_date or end_date:
            date_filter: dict = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = f"{end_date}T23:59:59Z"
            mongo_filter["created_at"] = date_filter

        cursor = self._collection.find(mongo_filter).sort("created_at", -1)
        documents = await cursor.to_list(length=None)
        return [_to_entity(document) for document in documents]

    async def create(self, attendance: AttendanceEntity) -> AttendanceEntity:
        document = _to_document(attendance)
        result = await self._collection.insert_one(document)
        created = await self._collection.find_one({"_id": result.inserted_id})
        return _to_entity(created)
