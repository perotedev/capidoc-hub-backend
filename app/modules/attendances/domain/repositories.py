from typing import Protocol

from app.modules.attendances.domain.entities import AttendanceEntity, AttendanceStats


class AttendanceRepository(Protocol):
    async def get_by_id(self, attendance_id: str) -> AttendanceEntity | None: ...

    async def search(self, query: str | None, form_id: str | None) -> list[AttendanceEntity]: ...

    async def search_by_form(
        self,
        form_id: str,
        query: str | None,
        start_date: str | None,
        end_date: str | None,
        field_id: str | None,
        field_value: str | None,
    ) -> list[AttendanceEntity]: ...

    async def get_stats(self, project_id: str | None, project_ids: list[str] | None = None) -> AttendanceStats: ...

    async def create(self, attendance: AttendanceEntity) -> AttendanceEntity: ...

    async def search_for_report(
        self,
        project_id: str,
        start_date: str | None,
        end_date: str | None,
        form_ids: list[str],
        operator_ids: list[str],
    ) -> list[AttendanceEntity]: ...
