from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.email import EmailService, get_email_service
from app.modules.users.application.services import UserService
from app.modules.users.domain.repositories import UserRepository
from app.modules.users.infrastructure.repository import SqlAlchemyUserRepository


def get_user_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_user_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> UserService:
    return UserService(repository, email_service)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
