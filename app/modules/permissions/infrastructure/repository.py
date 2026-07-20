from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.permissions.domain.entities import (
    PermissionGroupEntity,
    PermissionGroupSummary,
    ResourcePermission,
)
from app.modules.permissions.infrastructure.models import (
    GroupPermissionModel,
    PermissionGroupMemberModel,
    PermissionGroupModel,
    UserPermissionModel,
)
from app.modules.projects.infrastructure.models import ProjectModel
from app.shared.enums import Resource


def _group_to_entity(model: PermissionGroupModel) -> PermissionGroupEntity:
    return PermissionGroupEntity(
        id=model.id,
        name=model.name,
        description=model.description,
        project_id=model.project_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _permission_to_entity(model: GroupPermissionModel | UserPermissionModel) -> ResourcePermission:
    return ResourcePermission(
        resource=Resource(model.resource),
        can_create=model.can_create,
        can_read=model.can_read,
        can_update=model.can_update,
        can_delete=model.can_delete,
    )


class SqlAlchemyPermissionRepository:
    """Postgres-backed implementation of `PermissionGroupRepository` + `UserPermissionRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Groups ────────────────────────────────────────────────────────────

    async def get_by_id(self, group_id: UUID) -> PermissionGroupEntity | None:
        model = await self._session.get(PermissionGroupModel, group_id)
        return _group_to_entity(model) if model else None

    async def _build_summary(self, model: PermissionGroupModel, project_name: str) -> PermissionGroupSummary:
        members_count_result = await self._session.execute(
            select(func.count(PermissionGroupMemberModel.user_id)).where(
                PermissionGroupMemberModel.group_id == model.id
            )
        )
        members_count = members_count_result.scalar_one()
        permissions = await self.get_group_permissions(model.id)
        return PermissionGroupSummary(
            group=_group_to_entity(model),
            project_name=project_name,
            members_count=members_count,
            permissions=permissions,
        )

    async def get_summary_by_id(self, group_id: UUID) -> PermissionGroupSummary | None:
        result = await self._session.execute(
            select(PermissionGroupModel, ProjectModel.name)
            .join(ProjectModel, ProjectModel.id == PermissionGroupModel.project_id)
            .where(PermissionGroupModel.id == group_id)
        )
        row = result.first()
        if row is None:
            return None
        model, project_name = row
        return await self._build_summary(model, project_name)

    async def search(self, query: str | None, project_id: UUID | None) -> list[PermissionGroupSummary]:
        statement = select(PermissionGroupModel, ProjectModel.name).join(
            ProjectModel, ProjectModel.id == PermissionGroupModel.project_id
        )
        if project_id is not None:
            statement = statement.where(PermissionGroupModel.project_id == project_id)
        if query:
            like_pattern = f"%{query}%"
            statement = statement.where(
                PermissionGroupModel.name.ilike(like_pattern)
                | PermissionGroupModel.description.ilike(like_pattern)
            )
        result = await self._session.execute(statement.order_by(PermissionGroupModel.name))
        return [await self._build_summary(model, project_name) for model, project_name in result.all()]

    async def create(self, group: PermissionGroupEntity) -> PermissionGroupEntity:
        model = PermissionGroupModel(
            id=group.id, name=group.name, description=group.description, project_id=group.project_id
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _group_to_entity(model)

    async def update(self, group: PermissionGroupEntity) -> PermissionGroupEntity:
        model = await self._session.get(PermissionGroupModel, group.id)
        if model is None:
            raise ValueError(f"Permission group {group.id} not found")
        model.name = group.name
        model.description = group.description
        await self._session.commit()
        await self._session.refresh(model)
        return _group_to_entity(model)

    async def delete(self, group_id: UUID) -> None:
        model = await self._session.get(PermissionGroupModel, group_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()

    # ── Group permissions ────────────────────────────────────────────────

    async def get_group_permissions(self, group_id: UUID) -> list[ResourcePermission]:
        result = await self._session.execute(
            select(GroupPermissionModel).where(GroupPermissionModel.group_id == group_id)
        )
        return [_permission_to_entity(model) for model in result.scalars().all()]

    async def set_group_permissions(self, group_id: UUID, permissions: list[ResourcePermission]) -> None:
        await self._session.execute(
            delete(GroupPermissionModel).where(GroupPermissionModel.group_id == group_id)
        )
        for permission in permissions:
            self._session.add(
                GroupPermissionModel(
                    group_id=group_id,
                    resource=permission.resource.value,
                    can_create=permission.can_create,
                    can_read=permission.can_read,
                    can_update=permission.can_update,
                    can_delete=permission.can_delete,
                )
            )
        await self._session.commit()

    # ── Membership ───────────────────────────────────────────────────────

    async def get_member_ids(self, group_id: UUID) -> list[UUID]:
        result = await self._session.execute(
            select(PermissionGroupMemberModel.user_id).where(PermissionGroupMemberModel.group_id == group_id)
        )
        return list(result.scalars().all())

    async def set_members(self, group_id: UUID, user_ids: list[UUID]) -> None:
        await self._session.execute(
            delete(PermissionGroupMemberModel).where(PermissionGroupMemberModel.group_id == group_id)
        )
        for user_id in user_ids:
            self._session.add(PermissionGroupMemberModel(group_id=group_id, user_id=user_id))
        await self._session.commit()

    async def get_group_ids_for_user(self, user_id: UUID) -> list[UUID]:
        result = await self._session.execute(
            select(PermissionGroupMemberModel.group_id).where(PermissionGroupMemberModel.user_id == user_id)
        )
        return list(result.scalars().all())

    # ── Individual user permissions ──────────────────────────────────────

    async def get_user_permissions(self, user_id: UUID) -> list[ResourcePermission]:
        result = await self._session.execute(
            select(UserPermissionModel).where(UserPermissionModel.user_id == user_id)
        )
        return [_permission_to_entity(model) for model in result.scalars().all()]

    async def set_user_permissions(self, user_id: UUID, permissions: list[ResourcePermission]) -> None:
        await self._session.execute(delete(UserPermissionModel).where(UserPermissionModel.user_id == user_id))
        for permission in permissions:
            self._session.add(
                UserPermissionModel(
                    user_id=user_id,
                    resource=permission.resource.value,
                    can_create=permission.can_create,
                    can_read=permission.can_read,
                    can_update=permission.can_update,
                    can_delete=permission.can_delete,
                )
            )
        await self._session.commit()

    async def get_permissions_for_groups(self, group_ids: list[UUID]) -> list[ResourcePermission]:
        if not group_ids:
            return []
        result = await self._session.execute(
            select(GroupPermissionModel).where(GroupPermissionModel.group_id.in_(group_ids))
        )
        return [_permission_to_entity(model) for model in result.scalars().all()]
