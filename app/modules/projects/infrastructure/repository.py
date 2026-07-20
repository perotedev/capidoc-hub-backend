from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.departments.infrastructure.models import DepartmentModel
from app.modules.organizations.infrastructure.models import OrganizationModel
from app.modules.projects.domain.entities import ProjectEntity, ProjectSummary
from app.modules.projects.infrastructure.models import ProjectModel
from app.modules.users.infrastructure.models import UserModel


def _to_entity(model: ProjectModel) -> ProjectEntity:
    return ProjectEntity(
        id=model.id,
        name=model.name,
        description=model.description,
        cnpj=model.cnpj,
        org_id=model.org_id,
        active=model.active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyProjectRepository:
    """Postgres-backed implementation of `ProjectRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _summary_statement(self):
        users_count_subquery = (
            select(func.count(UserModel.id))
            .where(UserModel.project_id == ProjectModel.id)
            .scalar_subquery()
        )
        departments_count_subquery = (
            select(func.count(DepartmentModel.id))
            .where(DepartmentModel.project_id == ProjectModel.id)
            .scalar_subquery()
        )
        return select(
            ProjectModel,
            OrganizationModel.name,
            users_count_subquery.label("users_count"),
            departments_count_subquery.label("departments_count"),
        ).join(OrganizationModel, OrganizationModel.id == ProjectModel.org_id)

    async def _execute_summary(self, statement) -> list[ProjectSummary]:
        result = await self._session.execute(statement.order_by(ProjectModel.name))
        return [
            ProjectSummary(
                project=_to_entity(project_model),
                org_name=org_name,
                users_count=users_count,
                departments_count=departments_count,
            )
            for project_model, org_name, users_count, departments_count in result.all()
        ]

    async def get_by_id(self, project_id: UUID) -> ProjectEntity | None:
        model = await self._session.get(ProjectModel, project_id)
        return _to_entity(model) if model else None

    async def get_summary_by_id(self, project_id: UUID) -> ProjectSummary | None:
        statement = self._summary_statement().where(ProjectModel.id == project_id)
        summaries = await self._execute_summary(statement)
        return summaries[0] if summaries else None

    async def search(self, query: str | None, org_id: UUID | None = None) -> list[ProjectSummary]:
        statement = self._summary_statement()
        if org_id is not None:
            statement = statement.where(ProjectModel.org_id == org_id)
        if query:
            like_pattern = f"%{query}%"
            statement = statement.where(
                ProjectModel.name.ilike(like_pattern) | ProjectModel.description.ilike(like_pattern)
            )
        return await self._execute_summary(statement)

    async def create(self, project: ProjectEntity) -> ProjectEntity:
        model = ProjectModel(
            id=project.id,
            name=project.name,
            description=project.description,
            cnpj=project.cnpj,
            org_id=project.org_id,
            active=project.active,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, project: ProjectEntity) -> ProjectEntity:
        model = await self._session.get(ProjectModel, project.id)
        if model is None:
            raise ValueError(f"Project {project.id} not found")
        model.name = project.name
        model.description = project.description
        model.cnpj = project.cnpj
        model.active = project.active
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, project_id: UUID) -> None:
        model = await self._session.get(ProjectModel, project_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()
