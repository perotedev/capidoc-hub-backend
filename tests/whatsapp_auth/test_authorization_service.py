from datetime import date, timedelta

from app.modules.whatsapp_auth.application.services import WhatsAppAuthorizationService
from app.modules.whatsapp_auth.phone_utils import normalize_phone_number

from .conftest import make_authorization

_YESTERDAY = date.today() - timedelta(days=1)
_NEXT_WEEK = date.today() + timedelta(days=7)


def _service(repository) -> WhatsAppAuthorizationService:
    return WhatsAppAuthorizationService(repository, project_repository=None)  # unused by get_active_by_phone


class TestNormalizePhoneNumber:
    def test_strips_formatting(self):
        assert normalize_phone_number("+55 (11) 99999-0000") == "5511999990000"

    def test_strips_whatsapp_jid_suffix(self):
        assert normalize_phone_number("5511999990000@c.us") == "5511999990000"

    def test_already_normalized_is_unchanged(self):
        assert normalize_phone_number("5511999990000") == "5511999990000"


class TestGetActiveByPhone:
    async def test_active_authorization_is_returned(self, fake_repository):
        authorization = make_authorization(expires_at=_NEXT_WEEK)
        fake_repository.seed(authorization)
        service = _service(fake_repository)

        result = await service.get_active_by_phone(authorization.phone_number)

        assert result is not None
        assert result.id == authorization.id
        assert fake_repository.update_calls == []  # no renewal needed

    async def test_revoked_authorization_is_rejected_even_if_not_expired(self, fake_repository):
        authorization = make_authorization(expires_at=_NEXT_WEEK, revoked=True)
        fake_repository.seed(authorization)
        service = _service(fake_repository)

        result = await service.get_active_by_phone(authorization.phone_number)

        assert result is None

    async def test_unknown_phone_returns_none(self, fake_repository):
        service = _service(fake_repository)
        result = await service.get_active_by_phone("5511000000000")
        assert result is None

    async def test_expired_without_auto_renew_is_rejected(self, fake_repository):
        authorization = make_authorization(expires_at=_YESTERDAY, auto_renew=False)
        fake_repository.seed(authorization)
        service = _service(fake_repository)

        result = await service.get_active_by_phone(authorization.phone_number)

        assert result is None
        assert fake_repository.update_calls == []

    async def test_expired_with_auto_renew_is_renewed_and_accepted(self, fake_repository):
        authorization = make_authorization(expires_at=_YESTERDAY, auto_renew=True, validity_days=30)
        fake_repository.seed(authorization)
        service = _service(fake_repository)

        result = await service.get_active_by_phone(authorization.phone_number)

        assert result is not None
        assert result.expires_at > date.today()
        assert len(fake_repository.update_calls) == 1

    async def test_phone_lookup_is_normalized(self, fake_repository):
        authorization = make_authorization(phone_number="5511999990000", expires_at=_NEXT_WEEK)
        fake_repository.seed(authorization)
        service = _service(fake_repository)

        result = await service.get_active_by_phone("+55 (11) 99999-0000")

        assert result is not None
        assert result.id == authorization.id
