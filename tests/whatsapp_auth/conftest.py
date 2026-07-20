import uuid
from datetime import date, datetime, timezone

import pytest

from app.modules.whatsapp_auth.domain.entities import WhatsAppAuthorizationEntity


class FakeAuthorizationRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, WhatsAppAuthorizationEntity] = {}
        self.update_calls: list[WhatsAppAuthorizationEntity] = []

    def seed(self, authorization: WhatsAppAuthorizationEntity) -> None:
        self._by_id[authorization.id] = authorization

    async def get_by_id(self, authorization_id: uuid.UUID):
        return self._by_id.get(authorization_id)

    async def get_by_phone(self, phone_number: str):
        return next((a for a in self._by_id.values() if a.phone_number == phone_number), None)

    async def create(self, authorization: WhatsAppAuthorizationEntity) -> WhatsAppAuthorizationEntity:
        self._by_id[authorization.id] = authorization
        return authorization

    async def update(self, authorization: WhatsAppAuthorizationEntity) -> WhatsAppAuthorizationEntity:
        self._by_id[authorization.id] = authorization
        self.update_calls.append(authorization)
        return authorization

    async def search(self, query, project_id):
        return []

    async def delete(self, authorization_id: uuid.UUID) -> None:
        self._by_id.pop(authorization_id, None)


def make_authorization(**overrides) -> WhatsAppAuthorizationEntity:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        name="João Teste",
        phone_number="5511999990000",
        project_id=uuid.uuid4(),
        validity_days=30,
        expires_at=date(2026, 12, 31),
        auto_renew=False,
        revoked=False,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return WhatsAppAuthorizationEntity(**defaults)


@pytest.fixture
def fake_repository() -> FakeAuthorizationRepository:
    return FakeAuthorizationRepository()
