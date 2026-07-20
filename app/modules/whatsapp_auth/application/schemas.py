from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.modules.whatsapp_auth.domain.entities import WhatsAppAuthorizationStatus, WhatsAppAuthorizationSummary
from app.shared.schema import CamelCaseModel


class WhatsAppAuthorizationCreateRequest(CamelCaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone_number: str = Field(min_length=8, max_length=20)
    project_id: UUID
    validity_days: int = Field(default=30, ge=1, le=3650)
    auto_renew: bool = False


class WhatsAppAuthorizationUpdateRequest(CamelCaseModel):
    name: str | None = None
    project_id: UUID | None = None
    validity_days: int | None = Field(default=None, ge=1, le=3650)
    auto_renew: bool | None = None


class WhatsAppAuthorizationResponse(CamelCaseModel):
    id: UUID
    name: str
    phone_number: str
    project_id: UUID
    project_name: str
    status: WhatsAppAuthorizationStatus
    validity_days: int
    expires_at: date
    auto_renew: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_summary(cls, summary: WhatsAppAuthorizationSummary, today: date) -> "WhatsAppAuthorizationResponse":
        authorization = summary.authorization
        return cls(
            id=authorization.id,
            name=authorization.name,
            phone_number=authorization.phone_number,
            project_id=authorization.project_id,
            project_name=summary.project_name,
            status=authorization.status(today),
            validity_days=authorization.validity_days,
            expires_at=authorization.expires_at,
            auto_renew=authorization.auto_renew,
            created_at=authorization.created_at,
            updated_at=authorization.updated_at,
        )
