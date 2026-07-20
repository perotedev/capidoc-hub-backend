from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis

from app.core.email import EmailService, get_email_service
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.redis_client import get_redis_client
from app.core.security import InvalidTokenError, TokenType, decode_token
from app.modules.auth.application.services import AuthService
from app.modules.auth.domain.repositories import PasswordResetRepository, SessionRepository
from app.modules.auth.infrastructure.password_reset_repository import RedisPasswordResetRepository
from app.modules.auth.infrastructure.session_repository import RedisSessionRepository
from app.modules.users.api.v1.dependencies import UserServiceDep
from app.modules.users.application.services import UserService
from app.modules.users.domain.entities import UserEntity
from app.shared.enums import Role

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


def get_session_repository(redis_client: Annotated[Redis, Depends(get_redis_client)]) -> SessionRepository:
    return RedisSessionRepository(redis_client)


def get_password_reset_repository(
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> PasswordResetRepository:
    return RedisPasswordResetRepository(redis_client)


def get_auth_service(
    user_service: UserServiceDep,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    password_reset_repository: Annotated[PasswordResetRepository, Depends(get_password_reset_repository)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> AuthService:
    return AuthService(user_service, session_repository, password_reset_repository, email_service)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
    user_service: UserServiceDep,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
) -> UserEntity:
    try:
        payload = decode_token(token)
    except InvalidTokenError as error:
        raise UnauthorizedError("Invalid or expired token") from error

    if payload.token_type != TokenType.ACCESS:
        raise UnauthorizedError("Token is not an access token")

    user = await user_service.get_user(UUID(payload.subject))
    if not user.can_authenticate():
        raise UnauthorizedError("User is inactive")

    return user


CurrentUser = Annotated[UserEntity, Depends(get_current_user)]


def require_roles(*allowed_roles: Role):
    """Dependency factory that only lets requests through if the user's role is in `allowed_roles`."""

    def _check(current_user: CurrentUser) -> UserEntity:
        if current_user.role not in allowed_roles and not current_user.is_super_admin():
            raise ForbiddenError("You do not have permission to perform this action")
        return current_user

    return Depends(_check)
