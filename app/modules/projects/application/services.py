import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.modules.projects.application.schemas import ProjectCreateRequest, ProjectUpdateRequest
from app.modules.projects.domain.entities import ProjectEntity, ProjectSummary
from app.modules.projects.domain.repositories import ProjectRepository


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    async def get_project(self, project_id: UUID) -> ProjectEntity:
        project = await self._repository.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    async def get_project_summary(self, project_id: UUID) -> ProjectSummary:
        summary = await self._repository.get_summary_by_id(project_id)
        if summary is None:
            raise NotFoundError(f"Project {project_id} not found")
        return summary

    async def search(self, query: str | None) -> list[ProjectSummary]:
        return await self._repository.search(query)

    async def create_project(self, request: ProjectCreateRequest) -> ProjectEntity:
        now = datetime.now(timezone.utc)
        project = ProjectEntity(
            id=uuid.uuid4(),
            name=request.name,
            description=request.description,
            cnpj=request.cnpj,
            admin_id=request.admin_id,
            active=True,
            created_at=now,
            updated_at=now,
        )
        return await self._repository.create(project)

    async def update_project(self, project_id: UUID, request: ProjectUpdateRequest) -> ProjectEntity:
        project = await self.get_project(project_id)
        if request.name is not None:
            project.name = request.name
        if request.description is not None:
            project.description = request.description
        if request.cnpj is not None:
            project.cnpj = request.cnpj
        if request.admin_id is not None:
            project.admin_id = request.admin_id
        if request.active is not None:
            project.active = request.active
        return await self._repository.update(project)

    async def delete_project(self, project_id: UUID) -> None:
        await self.get_project(project_id)
        await self._repository.delete(project_id)
