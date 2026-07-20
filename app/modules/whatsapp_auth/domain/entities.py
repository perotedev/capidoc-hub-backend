from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class WhatsAppAuthorizationStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(slots=True)
class WhatsAppAuthorizationEntity:
    id: UUID
    name: str
    phone_number: str
    project_id: UUID
    validity_days: int
    expires_at: date
    auto_renew: bool
    revoked: bool
    created_at: datetime
    updated_at: datetime

    def status(self, today: date) -> WhatsAppAuthorizationStatus:
        if self.revoked:
            return WhatsAppAuthorizationStatus.REVOKED
        if self.expires_at < today:
            return WhatsAppAuthorizationStatus.EXPIRED
        return WhatsAppAuthorizationStatus.ACTIVE


@dataclass(slots=True)
class WhatsAppAuthorizationSummary:
    authorization: WhatsAppAuthorizationEntity
    project_name: str
