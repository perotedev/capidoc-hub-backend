from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.storage import StorageService, get_storage_service
from app.modules.activities.api.v1.dependencies import get_activity_service
from app.modules.activities.application.services import ActivityService
from app.modules.attendances.api.v1.dependencies import get_attendance_repository
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.forms.api.v1.dependencies import FormServiceDep
from app.modules.whatsapp_auth.api.v1.dependencies import WhatsAppAuthorizationServiceDep
from app.modules.whatsapp_bot.application.conversation_service import WhatsAppBotService
from app.modules.whatsapp_bot.domain.repositories import WhatsAppConversationRepository
from app.modules.whatsapp_bot.infrastructure.repository import SqlAlchemyWhatsAppConversationRepository


def get_whatsapp_conversation_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WhatsAppConversationRepository:
    return SqlAlchemyWhatsAppConversationRepository(session)


def get_whatsapp_bot_service(
    conversation_repository: Annotated[WhatsAppConversationRepository, Depends(get_whatsapp_conversation_repository)],
    authorization_service: WhatsAppAuthorizationServiceDep,
    form_service: FormServiceDep,
    attendance_repository: Annotated[AttendanceRepository, Depends(get_attendance_repository)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
    activity_service: Annotated[ActivityService, Depends(get_activity_service)],
) -> WhatsAppBotService:
    return WhatsAppBotService(
        conversation_repository, authorization_service, form_service, attendance_repository, storage, activity_service
    )


WhatsAppBotServiceDep = Annotated[WhatsAppBotService, Depends(get_whatsapp_bot_service)]
