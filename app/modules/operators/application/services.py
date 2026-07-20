from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.departments.domain.repositories import DepartmentRepository
from app.modules.forms.domain.entities import FormStatus
from app.modules.forms.domain.repositories import FormRepository
from app.modules.operators.domain.entities import OperatorReport, OperatorStats
from app.modules.projects.domain.repositories import ProjectRepository
from app.modules.users.application.services import UserService
from app.shared.enums import Role


class OperatorService:
    """Aggregates operator (role=USER — the field-app role since GESTOR/OPERADOR
    were retired) identity data from Postgres with their attendance activity
    from MongoDB into a single reporting view."""

    def __init__(
        self,
        user_service: UserService,
        attendance_repository: AttendanceRepository,
        project_repository: ProjectRepository,
        department_repository: DepartmentRepository,
        form_repository: FormRepository,
    ) -> None:
        self._user_service = user_service
        self._attendance_repository = attendance_repository
        self._project_repository = project_repository
        self._department_repository = department_repository
        self._form_repository = form_repository

    async def _today_completion_rate(self, operator_id: UUID, project_id: UUID | None, today_start: datetime) -> int:
        """% of the operator's assigned forms filled at least once today.

        "Assigned" is approximated as every PUBLISHED form in the operator's
        project (the domain has no per-operator form assignment yet). A day
        with no available forms counts as fully complete (nothing was owed).
        """
        if project_id is None:
            return 100

        available_forms = await self._form_repository.search(None, FormStatus.PUBLISHED, str(project_id))
        if not available_forms:
            return 100

        attendances = await self._attendance_repository.search(query=None, form_id=None)
        forms_filled_today = {
            a.form_id
            for a in attendances
            if a.operator_id == str(operator_id) and a.created_at >= today_start
        }
        available_form_ids = {form.id for form in available_forms}
        return round(len(forms_filled_today & available_form_ids) / len(available_form_ids) * 100)

    async def _build_stats(self, operator_id: UUID, project_id: UUID | None) -> OperatorStats:
        attendances = await self._attendance_repository.search(query=None, form_id=None)
        mine = [a for a in attendances if a.operator_id == str(operator_id)]

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        today_count = sum(1 for a in mine if a.created_at >= today_start)
        week_count = sum(1 for a in mine if a.created_at >= week_start)
        month_count = sum(1 for a in mine if a.created_at >= month_start)
        avg_duration = int(sum(a.duration for a in mine) / len(mine)) if mine else 0
        completion_rate = await self._today_completion_rate(operator_id, project_id, today_start)

        return OperatorStats(
            today_attendances=today_count,
            week_attendances=week_count,
            month_attendances=month_count,
            total_attendances=len(mine),
            avg_duration=avg_duration,
            completion_rate=completion_rate,
        )

    async def get_operator(self, operator_id: UUID) -> OperatorReport:
        user = await self._user_service.get_user(operator_id)
        if user.role != Role.USER:
            raise NotFoundError(f"Operator {operator_id} not found")

        project_name = None
        if user.project_id is not None:
            project = await self._project_repository.get_by_id(user.project_id)
            project_name = project.name if project else None

        department_name = None
        if user.department_id is not None:
            department = await self._department_repository.get_by_id(user.department_id)
            department_name = department.name if department else None

        stats = await self._build_stats(user.id, user.project_id)
        return OperatorReport(
            id=user.id,
            name=user.name,
            email=user.email,
            avatar_url=user.avatar_url,
            project_id=user.project_id,
            project_name=project_name,
            department_id=user.department_id,
            department_name=department_name,
            stats=stats,
        )

    async def list_operators(self, project_ids: list[UUID] | None) -> list[OperatorReport]:
        users = await self._user_service.search_users(query=None, role=Role.USER, project_ids=project_ids)
        return [await self.get_operator(user.id) for user in users]
