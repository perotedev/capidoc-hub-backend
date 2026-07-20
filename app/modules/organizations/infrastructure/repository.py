from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.domain.entities import OrganizationEntity
from app.modules.organizations.infrastructure.models import OrganizationModel
from app.modules.projects.infrastructure.models import ProjectModel
from app.modules.users.infrastructure.models import UserModel


def _to_entity(model: OrganizationModel) -> OrganizationEntity:
    return OrganizationEntity(
        id=model.id,
        name=model.name,
        admin_id=model.admin_id,
        active=model.active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyOrganizationRepository:
    """Postgres-backed implementation of `OrganizationRepository`.

    Deliberately exposes only identity + counts (never business content) — the
    application service composes this with cross-DB counts (Mongo forms/
    attendances) to build the metadata-only `OrganizationSummary`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organization_id: UUID) -> OrganizationEntity | None:
        model = await self._session.get(OrganizationModel, organization_id)
        return _to_entity(model) if model else None

    async def get_by_admin_id(self, admin_id: UUID) -> OrganizationEntity | None:
        result = await self._session.execute(
            select(OrganizationModel).where(OrganizationModel.admin_id == admin_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_all(self) -> list[OrganizationEntity]:
        result = await self._session.execute(select(OrganizationModel).order_by(OrganizationModel.name))
        return [_to_entity(model) for model in result.scalars().all()]

    async def create(self, organization: OrganizationEntity) -> OrganizationEntity:
        model = OrganizationModel(
            id=organization.id, name=organization.name, admin_id=organization.admin_id, active=organization.active
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, organization: OrganizationEntity) -> OrganizationEntity:
        model = await self._session.get(OrganizationModel, organization.id)
        if model is None:
            raise ValueError(f"Organization {organization.id} not found")
        model.name = organization.name
        model.active = organization.active
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_admin_info(self, admin_id: UUID) -> tuple[str, str] | None:
        result = await self._session.execute(select(UserModel.name, UserModel.email).where(UserModel.id == admin_id))
        row = result.first()
        return (row[0], row[1]) if row else None

    async def get_project_ids(self, organization_id: UUID) -> list[UUID]:
        result = await self._session.execute(select(ProjectModel.id).where(ProjectModel.org_id == organization_id))
        return [row[0] for row in result.all()]

    async def count_projects(self, organization_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count(ProjectModel.id)).where(ProjectModel.org_id == organization_id)
        )
        return result.scalar_one()

    async def count_users(self, organization_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count(UserModel.id))
            .join(ProjectModel, ProjectModel.id == UserModel.project_id)
            .where(ProjectModel.org_id == organization_id)
        )
        return result.scalar_one()
