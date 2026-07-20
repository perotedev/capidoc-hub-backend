from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.departments.domain.entities import DepartmentEntity, DepartmentSummary
from app.modules.departments.infrastructure.models import DepartmentModel
from app.modules.projects.infrastructure.models import ProjectModel
from app.modules.users.infrastructure.models import UserModel


def _to_entity(model: DepartmentModel) -> DepartmentEntity:
    return DepartmentEntity(
        id=model.id,
        name=model.name,
        description=model.description,
        project_id=model.project_id,
        parent_id=model.parent_id,
        active=model.active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyDepartmentRepository:
    """Postgres-backed implementation of `DepartmentRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _summary_statement(self):
        parent_alias = aliased(DepartmentModel)
        users_count_subquery = (
            select(func.count(UserModel.id))
            .where(UserModel.department_id == DepartmentModel.id)
            .scalar_subquery()
        )
        return (
            select(
                DepartmentModel,
                ProjectModel.name,
                parent_alias.name,
                users_count_subquery.label("users_count"),
            )
            .join(ProjectModel, ProjectModel.id == DepartmentModel.project_id)
            .outerjoin(parent_alias, parent_alias.id == DepartmentModel.parent_id)
        )

    async def get_by_id(self, department_id: UUID) -> DepartmentEntity | None:
        model = await self._session.get(DepartmentModel, department_id)
        return _to_entity(model) if model else None

    async def get_summary_by_id(self, department_id: UUID) -> DepartmentSummary | None:
        statement = self._summary_statement().where(DepartmentModel.id == department_id)
        summaries = await self._execute_summary(statement)
        return summaries[0] if summaries else None

    async def list_by_project(self, project_id: UUID) -> list[DepartmentSummary]:
        statement = self._summary_statement().where(DepartmentModel.project_id == project_id)
        return await self._execute_summary(statement)

    async def search(self, query: str | None, project_ids: list[UUID] | None = None) -> list[DepartmentSummary]:
        statement = self._summary_statement()
        if project_ids is not None:
            statement = statement.where(DepartmentModel.project_id.in_(project_ids))
        if query:
            like_pattern = f"%{query}%"
            statement = statement.where(
                DepartmentModel.name.ilike(like_pattern) | DepartmentModel.description.ilike(like_pattern)
            )
        return await self._execute_summary(statement)

    async def _execute_summary(self, statement) -> list[DepartmentSummary]:
        result = await self._session.execute(statement.order_by(DepartmentModel.name))
        return [
            DepartmentSummary(
                department=_to_entity(department_model),
                project_name=project_name,
                parent_name=parent_name,
                users_count=users_count,
            )
            for department_model, project_name, parent_name, users_count in result.all()
        ]

    async def create(self, department: DepartmentEntity) -> DepartmentEntity:
        model = DepartmentModel(
            id=department.id,
            name=department.name,
            description=department.description,
            project_id=department.project_id,
            parent_id=department.parent_id,
            active=department.active,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, department: DepartmentEntity) -> DepartmentEntity:
        model = await self._session.get(DepartmentModel, department.id)
        if model is None:
            raise ValueError(f"Department {department.id} not found")
        model.name = department.name
        model.description = department.description
        model.parent_id = department.parent_id
        model.active = department.active
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, department_id: UUID) -> None:
        model = await self._session.get(DepartmentModel, department_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()
