from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.projects.api.v1.dependencies import get_project_repository
from app.modules.projects.domain.repositories import ProjectRepository
from app.modules.whatsapp_auth.application.services import WhatsAppAuthorizationService
from app.modules.whatsapp_auth.domain.repositories import WhatsAppAuthorizationRepository
from app.modules.whatsapp_auth.infrastructure.repository import SqlAlchemyWhatsAppAuthorizationRepository


def get_whatsapp_authorization_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WhatsAppAuthorizationRepository:
    return SqlAlchemyWhatsAppAuthorizationRepository(session)


def get_whatsapp_authorization_service(
    repository: Annotated[WhatsAppAuthorizationRepository, Depends(get_whatsapp_authorization_repository)],
    project_repository: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> WhatsAppAuthorizationService:
    return WhatsAppAuthorizationService(repository, project_repository)


WhatsAppAuthorizationServiceDep = Annotated[WhatsAppAuthorizationService, Depends(get_whatsapp_authorization_service)]
