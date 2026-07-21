from app.core.cache import FileUrlCacheService
from app.core.exceptions import NotFoundError
from app.modules.attendances.application.schemas import (
    AttendanceDetailResponse,
    AttendancePhotoResponse,
    AttendanceStatsResponse,
)
from app.modules.attendances.domain.entities import AttendanceEntity
from app.modules.attendances.domain.repositories import AttendanceRepository


class AttendanceService:
    def __init__(self, repository: AttendanceRepository, file_url_cache: FileUrlCacheService) -> None:
        self._repository = repository
        self._file_url_cache = file_url_cache

    async def _to_detail_response(self, attendance: AttendanceEntity) -> AttendanceDetailResponse:
        photos = [
            AttendancePhotoResponse(
                id=photo.id,
                field_id=photo.field_id,
                caption=photo.caption,
                url=await self._file_url_cache.get_signed_url(photo.file_key),
            )
            for photo in attendance.photos
        ]
        return AttendanceDetailResponse(
            id=attendance.id,
            form_id=attendance.form_id,
            form_name=attendance.form_name,
            operator_id=attendance.operator_id,
            operator_name=attendance.operator_name,
            project_id=attendance.project_id,
            project_name=attendance.project_name,
            duration=attendance.duration,
            responses=attendance.responses,
            photos=photos,
            signature=attendance.signature,
            gps_location=attendance.gps_location,
            created_at=attendance.created_at,
            completed_at=attendance.completed_at,
            synced_at=attendance.synced_at,
        )

    async def get_attendance(self, attendance_id: str) -> AttendanceDetailResponse:
        attendance = await self._repository.get_by_id(attendance_id)
        if attendance is None:
            raise NotFoundError(f"Attendance {attendance_id} not found")
        return await self._to_detail_response(attendance)

    async def search(self, query: str | None, form_id: str | None) -> list[AttendanceEntity]:
        return await self._repository.search(query, form_id)

    async def search_by_form(
        self,
        form_id: str,
        query: str | None,
        start_date: str | None,
        end_date: str | None,
        field_id: str | None,
        field_value: str | None,
    ) -> list[AttendanceEntity]:
        return await self._repository.search_by_form(form_id, query, start_date, end_date, field_id, field_value)

    async def get_stats(self, project_id: str | None, project_ids: list[str] | None = None) -> AttendanceStatsResponse:
        stats = await self._repository.get_stats(project_id, project_ids)
        return AttendanceStatsResponse(**stats.model_dump())

    async def create_attendance(self, attendance: AttendanceEntity) -> AttendanceEntity:
        return await self._repository.create(attendance)
