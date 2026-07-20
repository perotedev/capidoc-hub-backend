from datetime import datetime, timezone
from uuid import UUID

from app.core.config import get_settings
from app.core.email import EmailService
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.modules.auth.application.schemas import LoginRequest, TokenResponse
from app.modules.auth.domain.entities import UserSession
from app.modules.auth.domain.repositories import PasswordResetRepository, SessionRepository
from app.modules.users.application.schemas import UserResponse
from app.modules.users.application.services import UserService
from app.modules.users.domain.entities import UserEntity

settings = get_settings()


class AuthService:
    """Handles login, token refresh/rotation, session lifecycle and password recovery."""

    def __init__(
        self,
        user_service: UserService,
        session_repository: SessionRepository,
        password_reset_repository: PasswordResetRepository,
        email_service: EmailService,
    ) -> None:
        self._user_service = user_service
        self._session_repository = session_repository
        self._password_reset_repository = password_reset_repository
        self._email_service = email_service

    async def login(self, request: LoginRequest, user_agent: str | None) -> TokenResponse:
        user = await self._user_service.get_by_email(request.email)
        if user is None or not user.can_authenticate() or not verify_password(request.password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        return await self._issue_tokens(user, user_agent)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = self._decode_refresh_token(refresh_token)
        user_id = UUID(payload_subject := payload.subject)

        session = await self._session_repository.get_session(user_id, payload.jti)
        if session is None:
            raise UnauthorizedError("Session expired or revoked")

        user = await self._user_service.get_user(UUID(payload_subject))
        if not user.can_authenticate():
            raise UnauthorizedError("User is inactive")

        await self._session_repository.delete_session(user_id, payload.jti)
        return await self._issue_tokens(user, session.user_agent)

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except InvalidTokenError:
            return
        await self._session_repository.delete_session(UUID(payload.subject), payload.jti)

    async def logout_all(self, user_id: UUID) -> None:
        await self._session_repository.delete_all_sessions(user_id)

    async def list_sessions(self, user_id: UUID) -> list[UserSession]:
        return await self._session_repository.list_sessions(user_id)

    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        user = await self._user_service.get_user(user_id)
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect")
        await self._user_service.change_password(user_id, new_password)
        await self._session_repository.delete_all_sessions(user_id)

    async def request_password_reset(self, email: str) -> None:
        """Silently no-ops for unknown emails, to avoid leaking which addresses are registered."""
        user = await self._user_service.get_by_email(email)
        if user is None:
            return
        token = await self._password_reset_repository.create_token(user.id)
        reset_link = f"{settings.frontend_url}/login/recover-password?token={token}"
        await self._email_service.send_password_recovery_email(user.email, reset_link)

    async def reset_password(self, token: str, new_password: str) -> None:
        user_id = await self._password_reset_repository.get_user_id(token)
        if user_id is None:
            raise UnauthorizedError("Invalid or expired password reset token")
        await self._user_service.change_password(user_id, new_password)
        await self._password_reset_repository.delete_token(token)
        await self._session_repository.delete_all_sessions(user_id)

    def _decode_refresh_token(self, refresh_token: str):
        try:
            payload = decode_token(refresh_token)
        except InvalidTokenError as error:
            raise UnauthorizedError("Invalid refresh token") from error
        if payload.token_type != TokenType.REFRESH:
            raise UnauthorizedError("Token is not a refresh token")
        return payload

    async def _issue_tokens(self, user: UserEntity, user_agent: str | None) -> TokenResponse:
        access_token, _ = create_access_token(str(user.id))
        refresh_token, refresh_jti = create_refresh_token(str(user.id))
        refresh_payload = decode_token(refresh_token)

        session = UserSession(
            user_id=user.id,
            session_id=refresh_jti,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
            expires_at=refresh_payload.expires_at,
        )
        await self._session_repository.create_session(session)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )
