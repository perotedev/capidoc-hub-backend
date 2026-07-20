from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.whatsapp_bot.domain.entities import (
    ConversationState,
    WhatsAppConversationEntity,
    WhatsAppPhotoAnswer,
    WhatsAppTextAnswer,
)
from app.modules.whatsapp_bot.infrastructure.models import WhatsAppConversationModel


def _to_entity(model: WhatsAppConversationModel) -> WhatsAppConversationEntity:
    return WhatsAppConversationEntity(
        id=model.id,
        phone_number=model.phone_number,
        authorization_id=model.authorization_id,
        state=ConversationState(model.state),
        form_id=model.form_id,
        current_field_index=model.current_field_index,
        created_at=model.created_at,
        updated_at=model.updated_at,
        pending_options=list(model.pending_options),
        text_answers=[WhatsAppTextAnswer(**item) for item in model.text_answers],
        photo_answers=[WhatsAppPhotoAnswer(**item) for item in model.photo_answers],
    )


class SqlAlchemyWhatsAppConversationRepository:
    """Postgres-backed implementation of `WhatsAppConversationRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_phone(self, phone_number: str) -> WhatsAppConversationEntity | None:
        statement = select(WhatsAppConversationModel).where(WhatsAppConversationModel.phone_number == phone_number)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def create(self, conversation: WhatsAppConversationEntity) -> WhatsAppConversationEntity:
        model = WhatsAppConversationModel(
            id=conversation.id,
            phone_number=conversation.phone_number,
            authorization_id=conversation.authorization_id,
            state=conversation.state.value,
            form_id=conversation.form_id,
            current_field_index=conversation.current_field_index,
            pending_options=list(conversation.pending_options),
            text_answers=[],
            photo_answers=[],
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, conversation: WhatsAppConversationEntity) -> WhatsAppConversationEntity:
        model = await self._session.get(WhatsAppConversationModel, conversation.id)
        if model is None:
            raise ValueError(f"WhatsApp conversation {conversation.id} not found")
        model.state = conversation.state.value
        model.form_id = conversation.form_id
        model.current_field_index = conversation.current_field_index
        model.pending_options = list(conversation.pending_options)
        model.text_answers = [
            {"field_id": item.field_id, "field_label": item.field_label, "value": item.value}
            for item in conversation.text_answers
        ]
        model.photo_answers = [
            {"field_id": item.field_id, "caption": item.caption, "file_key": item.file_key}
            for item in conversation.photo_answers
        ]
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete_by_phone(self, phone_number: str) -> None:
        statement = delete(WhatsAppConversationModel).where(WhatsAppConversationModel.phone_number == phone_number)
        await self._session.execute(statement)
        await self._session.commit()
