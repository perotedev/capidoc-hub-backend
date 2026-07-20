"""Fakes for `WhatsAppBotService`'s dependencies.

None of these formally implement their real Protocol/class — Python doesn't
enforce that at runtime, and only the methods `WhatsAppBotService` actually
calls are implemented, keeping each fake small and easy to read.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest

from app.modules.forms.domain.entities import FormEntity, FormStatus


@dataclass
class FakeAuthorization:
    """Stands in for both `WhatsAppAuthorizationEntity` (returned by
    `get_active_by_phone`) and `WhatsAppAuthorizationResponse` (returned by
    `get`) — the conversation service only ever reads `id`/`name`/
    `project_id`/`project_name` from either, so one shape covers both."""

    id: uuid.UUID
    name: str
    project_id: uuid.UUID
    project_name: str = "Projeto Teste"


class FakeAuthorizationService:
    def __init__(self, authorization: FakeAuthorization | None) -> None:
        self._authorization = authorization

    async def get_active_by_phone(self, phone_number: str) -> FakeAuthorization | None:
        return self._authorization

    async def get(self, authorization_id: uuid.UUID) -> FakeAuthorization:
        assert self._authorization is not None
        return self._authorization


class FakeFormService:
    def __init__(self, forms: list[FormEntity]) -> None:
        self._forms = {form.id: form for form in forms}
        self.notified_form_ids: list[str] = []

    async def get_form(self, form_id: str) -> FormEntity:
        return self._forms[form_id]

    async def search(self, query, status, project_id) -> list[FormEntity]:
        return [
            form for form in self._forms.values()
            if form.project_id == project_id and form.status == status
        ]

    async def notify_attendance_submitted(self, form_id: str) -> None:
        self.notified_form_ids.append(form_id)


class FakeConversationRepository:
    def __init__(self) -> None:
        self._by_phone: dict[str, object] = {}

    async def get_by_phone(self, phone_number: str):
        return self._by_phone.get(phone_number)

    async def create(self, conversation):
        self._by_phone[conversation.phone_number] = conversation
        return conversation

    async def update(self, conversation):
        self._by_phone[conversation.phone_number] = conversation
        return conversation

    async def delete_by_phone(self, phone_number: str) -> None:
        self._by_phone.pop(phone_number, None)


class FakeAttendanceRepository:
    def __init__(self) -> None:
        self.created: list = []

    async def create(self, attendance):
        attendance.id = f"fake-attendance-{len(self.created)}"
        self.created.append(attendance)
        return attendance


class FakeStorageService:
    def __init__(self) -> None:
        self.uploaded: list[tuple[str, bytes, str]] = []

    async def upload_file(self, key: str, content: bytes, content_type: str) -> None:
        self.uploaded.append((key, content, content_type))


class FakeActivityService:
    def __init__(self) -> None:
        self.logged: list[tuple] = []

    async def log(self, *args, **kwargs) -> None:
        self.logged.append(("log", args, kwargs))

    async def log_for_project(self, *args, **kwargs) -> None:
        self.logged.append(("log_for_project", args, kwargs))


def make_form(**overrides) -> FormEntity:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id="form-1",
        name="Vistoria",
        project_id=str(uuid.uuid4()),
        status=FormStatus.PUBLISHED,
        fields=[],
        created_by="creator-1",
        created_by_name="Creator",
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return FormEntity(**defaults)


@pytest.fixture
def fake_conversations() -> FakeConversationRepository:
    return FakeConversationRepository()


@pytest.fixture
def fake_attendances() -> FakeAttendanceRepository:
    return FakeAttendanceRepository()


@pytest.fixture
def fake_storage() -> FakeStorageService:
    return FakeStorageService()


@pytest.fixture
def fake_activities() -> FakeActivityService:
    return FakeActivityService()
