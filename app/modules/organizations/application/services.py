import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.forms.domain.repositories import FormRepository
from app.modules.organizations.application.schemas import OrganizationCreateRequest, OrganizationUpdateRequest
from app.modules.organizations.domain.entities import OrganizationEntity, OrganizationSummary
from app.modules.organizations.domain.repositories import OrganizationRepository
from app.modules.users.application.schemas import UserCreateRequest
from app.modules.users.application.services import UserService
from app.shared.enums import Role


class OrganizationService:
    """SUPER_ADMIN-only: manages tenants (organizations) and their owning ADMIN
    account. Never exposes tenant content — only identity + counts."""

    def __init__(
        self,
        repository: OrganizationRepository,
        user_service: UserService,
        form_repository: FormRepository,
        attendance_repository: AttendanceRepository,
    ) -> None:
        self._repository = repository
        self._user_service = user_service
        self._form_repository = form_repository
        self._attendance_repository = attendance_repository

    async def _build_summary(self, organization: OrganizationEntity) -> OrganizationSummary:
        admin = await self._user_service.get_user(organization.admin_id)
        project_ids = await self._repository.get_project_ids(organization.id)
        project_id_strings = {str(project_id) for project_id in project_ids}

        forms_count = 0
        attendances_count = 0
        if project_ids:
            all_forms = await self._form_repository.search(None, None, None)
            forms_count = sum(1 for form in all_forms if form.project_id in project_id_strings)

            all_attendances = await self._attendance_repository.search(None, None)
            attendances_count = sum(1 for attendance in all_attendances if attendance.project_id in project_id_strings)

        return OrganizationSummary(
            organization=organization,
            admin_name=admin.name,
            admin_email=admin.email,
            projects_count=await self._repository.count_projects(organization.id),
            users_count=await self._repository.count_users(organization.id),
            forms_count=forms_count,
            attendances_count=attendances_count,
        )

    async def get_organization(self, organization_id: UUID) -> OrganizationSummary:
        organization = await self._repository.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError(f"Organization {organization_id} not found")
        return await self._build_summary(organization)

    async def list_organizations(self) -> list[OrganizationSummary]:
        organizations = await self._repository.list_all()
        return [await self._build_summary(organization) for organization in organizations]

    async def create_organization(self, request: OrganizationCreateRequest) -> OrganizationSummary:
        existing_admin = await self._user_service.get_by_email(request.admin_email)
        if existing_admin is not None:
            raise ConflictError(f"A user with email {request.admin_email} already exists")

        admin_user = await self._user_service.create_user(
            UserCreateRequest(
                name=request.admin_name,
                email=request.admin_email,
                password=request.admin_password,
                role=Role.ADMIN,
                project_id=None,
                department_id=None,
            )
        )

        now = datetime.now(timezone.utc)
        organization = OrganizationEntity(
            id=uuid.uuid4(), name=request.name, admin_id=admin_user.id, active=True, created_at=now, updated_at=now
        )
        created = await self._repository.create(organization)
        return await self._build_summary(created)

    async def update_organization(self, organization_id: UUID, request: OrganizationUpdateRequest) -> OrganizationSummary:
        organization = await self._repository.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError(f"Organization {organization_id} not found")
        if request.name is not None:
            organization.name = request.name
        if request.active is not None:
            organization.active = request.active
        updated = await self._repository.update(organization)
        return await self._build_summary(updated)
