from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.departments.infrastructure.models import DepartmentModel
from app.modules.projects.infrastructure.models import ProjectModel
from app.modules.users.domain.entities import UserEntity, UserSummary
from app.modules.users.infrastructure.models import UserModel
from app.shared.enums import Role


def _to_entity(model: UserModel) -> UserEntity:
    return UserEntity(
        id=model.id,
        name=model.name,
        email=model.email,
        password_hash=model.password_hash,
        cpf=model.cpf,
        phone=model.phone,
        role=Role(model.role),
        project_id=model.project_id,
        department_id=model.department_id,
        avatar_url=model.avatar_url,
        active=model.active,
        first_access=model.first_access,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyUserRepository:
    """Postgres-backed implementation of `UserRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> UserEntity | None:
        model = await self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> UserEntity | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    def _summary_statement(self):
        return (
            select(UserModel, ProjectModel.name, DepartmentModel.name)
            .outerjoin(ProjectModel, ProjectModel.id == UserModel.project_id)
            .outerjoin(DepartmentModel, DepartmentModel.id == UserModel.department_id)
        )

    async def get_summary_by_id(self, user_id: UUID) -> UserSummary | None:
        result = await self._session.execute(self._summary_statement().where(UserModel.id == user_id))
        row = result.first()
        if row is None:
            return None
        model, project_name, department_name = row
        return UserSummary(user=_to_entity(model), project_name=project_name, department_name=department_name)

    async def search_summary(
        self,
        query: str | None,
        role: Role | None,
        project_ids: list[UUID] | None,
    ) -> list[UserSummary]:
        statement = self._summary_statement()
        if project_ids is not None:
            statement = statement.where(UserModel.project_id.in_(project_ids))
        if role is not None:
            statement = statement.where(UserModel.role == role.value)
        if query:
            like_pattern = f"%{query}%"
            statement = statement.where(
                or_(UserModel.name.ilike(like_pattern), UserModel.email.ilike(like_pattern))
            )
        result = await self._session.execute(statement.order_by(UserModel.name))
        return [
            UserSummary(user=_to_entity(model), project_name=project_name, department_name=department_name)
            for model, project_name, department_name in result.all()
        ]

    async def list_by_project(self, project_ids: list[UUID] | None) -> list[UserEntity]:
        statement = select(UserModel)
        if project_ids is not None:
            statement = statement.where(UserModel.project_id.in_(project_ids))
        result = await self._session.execute(statement.order_by(UserModel.name))
        return [_to_entity(model) for model in result.scalars().all()]

    async def search(
        self,
        query: str | None,
        role: Role | None,
        project_ids: list[UUID] | None,
    ) -> list[UserEntity]:
        statement = select(UserModel)
        if project_ids is not None:
            statement = statement.where(UserModel.project_id.in_(project_ids))
        if role is not None:
            statement = statement.where(UserModel.role == role.value)
        if query:
            like_pattern = f"%{query}%"
            statement = statement.where(
                or_(UserModel.name.ilike(like_pattern), UserModel.email.ilike(like_pattern))
            )
        result = await self._session.execute(statement.order_by(UserModel.name))
        return [_to_entity(model) for model in result.scalars().all()]

    async def create(self, user: UserEntity) -> UserEntity:
        model = UserModel(
            id=user.id,
            name=user.name,
            email=user.email,
            password_hash=user.password_hash,
            cpf=user.cpf,
            phone=user.phone,
            role=user.role.value,
            project_id=user.project_id,
            department_id=user.department_id,
            avatar_url=user.avatar_url,
            active=user.active,
            first_access=user.first_access,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, user: UserEntity) -> UserEntity:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            raise ValueError(f"User {user.id} not found")
        model.name = user.name
        model.email = user.email
        model.password_hash = user.password_hash
        model.cpf = user.cpf
        model.phone = user.phone
        model.role = user.role.value
        model.project_id = user.project_id
        model.department_id = user.department_id
        model.avatar_url = user.avatar_url
        model.active = user.active
        model.first_access = user.first_access
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, user_id: UUID) -> None:
        model = await self._session.get(UserModel, user_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()
