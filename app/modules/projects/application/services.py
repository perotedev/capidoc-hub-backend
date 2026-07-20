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

    async def get_project(self, project_id: UUID, org_id: UUID) -> ProjectEntity:
        project = await self._repository.get_by_id(project_id)
        if project is None or project.org_id != org_id:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    async def get_project_summary(self, project_id: UUID, org_id: UUID) -> ProjectSummary:
        summary = await self._repository.get_summary_by_id(project_id)
        if summary is None or summary.project.org_id != org_id:
            raise NotFoundError(f"Project {project_id} not found")
        return summary

    async def search(self, query: str | None, org_id: UUID) -> list[ProjectSummary]:
        return await self._repository.search(query, org_id)

    async def create_project(self, request: ProjectCreateRequest, org_id: UUID) -> ProjectEntity:
        now = datetime.now(timezone.utc)
        project = ProjectEntity(
            id=uuid.uuid4(),
            name=request.name,
            description=request.description,
            cnpj=request.cnpj,
            org_id=org_id,
            active=True,
            created_at=now,
            updated_at=now,
        )
        return await self._repository.create(project)

    async def update_project(self, project_id: UUID, request: ProjectUpdateRequest, org_id: UUID) -> ProjectEntity:
        project = await self.get_project(project_id, org_id)
        if request.name is not None:
            project.name = request.name
        if request.description is not None:
            project.description = request.description
        if request.cnpj is not None:
            project.cnpj = request.cnpj
        if request.active is not None:
            project.active = request.active
        return await self._repository.update(project)

    async def delete_project(self, project_id: UUID, org_id: UUID) -> None:
        await self.get_project(project_id, org_id)
        await self._repository.delete(project_id)
