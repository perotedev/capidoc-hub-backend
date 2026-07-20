import uuid
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.projects.domain.repositories import ProjectRepository
from app.modules.whatsapp_auth.application.schemas import (
    WhatsAppAuthorizationCreateRequest,
    WhatsAppAuthorizationResponse,
    WhatsAppAuthorizationUpdateRequest,
)
from app.modules.whatsapp_auth.domain.entities import WhatsAppAuthorizationEntity
from app.modules.whatsapp_auth.domain.repositories import WhatsAppAuthorizationRepository
from app.modules.whatsapp_auth.phone_utils import normalize_phone_number


class WhatsAppAuthorizationService:
    """Manages the admin-controlled allowlist of phone numbers permitted to
    use the WhatsApp form-filling bot — including the validity window and
    optional auto-renewal, since the bot itself never re-authenticates a
    number beyond checking this list."""

    def __init__(self, repository: WhatsAppAuthorizationRepository, project_repository: ProjectRepository) -> None:
        self._repository = repository
        self._project_repository = project_repository

    async def _get_summary_response(self, authorization_id: UUID) -> WhatsAppAuthorizationResponse:
        authorization = await self._repository.get_by_id(authorization_id)
        if authorization is None:
            raise NotFoundError(f"WhatsApp authorization {authorization_id} not found")
        project = await self._project_repository.get_by_id(authorization.project_id)
        project_name = project.name if project else ""
        return WhatsAppAuthorizationResponse(
            id=authorization.id,
            name=authorization.name,
            phone_number=authorization.phone_number,
            project_id=authorization.project_id,
            project_name=project_name,
            status=authorization.status(date.today()),
            validity_days=authorization.validity_days,
            expires_at=authorization.expires_at,
            auto_renew=authorization.auto_renew,
            created_at=authorization.created_at,
            updated_at=authorization.updated_at,
        )

    async def get(self, authorization_id: UUID) -> WhatsAppAuthorizationResponse:
        return await self._get_summary_response(authorization_id)

    async def search(self, query: str | None, project_id: UUID | None) -> list[WhatsAppAuthorizationResponse]:
        today = date.today()
        summaries = await self._repository.search(query, project_id)
        return [WhatsAppAuthorizationResponse.from_summary(summary, today) for summary in summaries]

    async def create(self, request: WhatsAppAuthorizationCreateRequest) -> WhatsAppAuthorizationResponse:
        phone_number = normalize_phone_number(request.phone_number)
        now = datetime.now(timezone.utc)
        authorization = WhatsAppAuthorizationEntity(
            id=uuid.uuid4(),
            name=request.name,
            phone_number=phone_number,
            project_id=request.project_id,
            validity_days=request.validity_days,
            expires_at=date.today() + timedelta(days=request.validity_days),
            auto_renew=request.auto_renew,
            revoked=False,
            created_at=now,
            updated_at=now,
        )
        try:
            created = await self._repository.create(authorization)
        except IntegrityError as error:
            raise ConflictError(f"A number {phone_number} is already registered") from error
        return await self._get_summary_response(created.id)

    async def update(
        self, authorization_id: UUID, request: WhatsAppAuthorizationUpdateRequest
    ) -> WhatsAppAuthorizationResponse:
        authorization = await self._repository.get_by_id(authorization_id)
        if authorization is None:
            raise NotFoundError(f"WhatsApp authorization {authorization_id} not found")
        if request.name is not None:
            authorization.name = request.name
        if request.project_id is not None:
            authorization.project_id = request.project_id
        if request.validity_days is not None:
            authorization.validity_days = request.validity_days
        if request.auto_renew is not None:
            authorization.auto_renew = request.auto_renew
        await self._repository.update(authorization)
        return await self._get_summary_response(authorization_id)

    async def revoke(self, authorization_id: UUID) -> WhatsAppAuthorizationResponse:
        authorization = await self._repository.get_by_id(authorization_id)
        if authorization is None:
            raise NotFoundError(f"WhatsApp authorization {authorization_id} not found")
        authorization.revoked = True
        await self._repository.update(authorization)
        return await self._get_summary_response(authorization_id)

    async def renew(self, authorization_id: UUID) -> WhatsAppAuthorizationResponse:
        """Manually extends the validity window from today — available even
        when `auto_renew` is off, so an admin can always grant more time."""
        authorization = await self._repository.get_by_id(authorization_id)
        if authorization is None:
            raise NotFoundError(f"WhatsApp authorization {authorization_id} not found")
        authorization.expires_at = date.today() + timedelta(days=authorization.validity_days)
        authorization.revoked = False
        await self._repository.update(authorization)
        return await self._get_summary_response(authorization_id)

    async def delete(self, authorization_id: UUID) -> None:
        await self._repository.delete(authorization_id)

    async def get_active_by_phone(self, raw_phone_number: str) -> WhatsAppAuthorizationEntity | None:
        """The bot's actual gate — looks up an authorization by phone,
        lazily auto-renews it if it lapsed and `auto_renew` is on, and
        returns it only if it's genuinely usable right now (not revoked, not
        expired even after the auto-renew check)."""
        phone_number = normalize_phone_number(raw_phone_number)
        authorization = await self._repository.get_by_phone(phone_number)
        if authorization is None or authorization.revoked:
            return None

        today = date.today()
        if authorization.expires_at < today:
            if not authorization.auto_renew:
                return None
            authorization.expires_at = today + timedelta(days=authorization.validity_days)
            authorization = await self._repository.update(authorization)

        return authorization
