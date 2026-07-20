from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.infrastructure.models import ProjectModel
from app.modules.whatsapp_auth.domain.entities import WhatsAppAuthorizationEntity, WhatsAppAuthorizationSummary
from app.modules.whatsapp_auth.infrastructure.models import WhatsAppAuthorizationModel


def _to_entity(model: WhatsAppAuthorizationModel) -> WhatsAppAuthorizationEntity:
    return WhatsAppAuthorizationEntity(
        id=model.id,
        name=model.name,
        phone_number=model.phone_number,
        project_id=model.project_id,
        validity_days=model.validity_days,
        expires_at=model.expires_at,
        auto_renew=model.auto_renew,
        revoked=model.revoked,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyWhatsAppAuthorizationRepository:
    """Postgres-backed implementation of `WhatsAppAuthorizationRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, authorization_id: UUID) -> WhatsAppAuthorizationEntity | None:
        model = await self._session.get(WhatsAppAuthorizationModel, authorization_id)
        return _to_entity(model) if model else None

    async def get_by_phone(self, phone_number: str) -> WhatsAppAuthorizationEntity | None:
        statement = select(WhatsAppAuthorizationModel).where(WhatsAppAuthorizationModel.phone_number == phone_number)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def search(self, query: str | None, project_id: UUID | None) -> list[WhatsAppAuthorizationSummary]:
        statement = select(WhatsAppAuthorizationModel, ProjectModel.name).join(
            ProjectModel, ProjectModel.id == WhatsAppAuthorizationModel.project_id
        )
        if project_id is not None:
            statement = statement.where(WhatsAppAuthorizationModel.project_id == project_id)
        if query:
            statement = statement.where(
                WhatsAppAuthorizationModel.name.ilike(f"%{query}%")
                | WhatsAppAuthorizationModel.phone_number.ilike(f"%{query}%")
            )
        result = await self._session.execute(statement.order_by(WhatsAppAuthorizationModel.created_at.desc()))
        return [
            WhatsAppAuthorizationSummary(authorization=_to_entity(model), project_name=project_name)
            for model, project_name in result.all()
        ]

    async def create(self, authorization: WhatsAppAuthorizationEntity) -> WhatsAppAuthorizationEntity:
        model = WhatsAppAuthorizationModel(
            id=authorization.id,
            name=authorization.name,
            phone_number=authorization.phone_number,
            project_id=authorization.project_id,
            validity_days=authorization.validity_days,
            expires_at=authorization.expires_at,
            auto_renew=authorization.auto_renew,
            revoked=authorization.revoked,
        )
        self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, authorization: WhatsAppAuthorizationEntity) -> WhatsAppAuthorizationEntity:
        model = await self._session.get(WhatsAppAuthorizationModel, authorization.id)
        if model is None:
            raise ValueError(f"WhatsApp authorization {authorization.id} not found")
        model.name = authorization.name
        model.phone_number = authorization.phone_number
        model.project_id = authorization.project_id
        model.validity_days = authorization.validity_days
        model.expires_at = authorization.expires_at
        model.auto_renew = authorization.auto_renew
        model.revoked = authorization.revoked
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, authorization_id: UUID) -> None:
        model = await self._session.get(WhatsAppAuthorizationModel, authorization_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()
