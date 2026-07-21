import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.departments.application.schemas import DepartmentCreateRequest, DepartmentUpdateRequest
from app.modules.departments.domain.entities import DepartmentEntity, DepartmentSummary
from app.modules.departments.domain.repositories import DepartmentRepository


class DepartmentService:
    def __init__(self, repository: DepartmentRepository) -> None:
        self._repository = repository

    async def get_department(self, department_id: UUID) -> DepartmentEntity:
        department = await self._repository.get_by_id(department_id)
        if department is None:
            raise NotFoundError(f"Department {department_id} not found")
        return department

    async def get_department_summary(self, department_id: UUID) -> DepartmentSummary:
        summary = await self._repository.get_summary_by_id(department_id)
        if summary is None:
            raise NotFoundError(f"Department {department_id} not found")
        return summary

    async def list_by_project(self, project_id: UUID) -> list[DepartmentSummary]:
        return await self._repository.list_by_project(project_id)

    async def search(self, query: str | None, project_ids: list[UUID] | None = None) -> list[DepartmentSummary]:
        return await self._repository.search(query, project_ids)

    async def create_department(self, request: DepartmentCreateRequest) -> DepartmentEntity:
        now = datetime.now(timezone.utc)
        department = DepartmentEntity(
            id=uuid.uuid4(),
            name=request.name,
            description=request.description,
            project_id=request.project_id,
            parent_id=request.parent_id,
            active=True,
            created_at=now,
            updated_at=now,
        )
        return await self._repository.create(department)

    async def update_department(self, department_id: UUID, request: DepartmentUpdateRequest) -> DepartmentEntity:
        department = await self.get_department(department_id)
        if request.name is not None:
            department.name = request.name
        if request.description is not None:
            department.description = request.description
        if "parent_id" in request.model_fields_set:
            if request.parent_id == department_id:
                raise BusinessRuleError("A department cannot be its own parent")
            department.parent_id = request.parent_id
        if request.active is not None:
            department.active = request.active
        return await self._repository.update(department)

    async def delete_department(self, department_id: UUID) -> None:
        await self.get_department(department_id)
        await self._repository.delete(department_id)
