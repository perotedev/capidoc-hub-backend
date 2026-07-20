import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.forms.domain.entities import FieldType, FormField, FormFieldOption
from app.modules.whatsapp_bot.application.conversation_service import WhatsAppBotService
from app.modules.whatsapp_bot.application.schemas import WhatsAppIncomingMessageRequest
from app.modules.whatsapp_bot.domain.entities import ConversationState

from .conftest import (
    FakeActivityService,
    FakeAttendanceRepository,
    FakeAuthorization,
    FakeAuthorizationService,
    FakeConversationRepository,
    FakeFormService,
    FakeStorageService,
    make_form,
)


def _msg(phone: str = "5511999990000", text: str | None = None, **kwargs) -> WhatsAppIncomingMessageRequest:
    return WhatsAppIncomingMessageRequest(phone_number=phone, text=text, **kwargs)


def _service(
    conversations: FakeConversationRepository,
    authorization: FakeAuthorization | None,
    forms: list,
    attendances: FakeAttendanceRepository,
    storage: FakeStorageService,
    activities: FakeActivityService,
) -> WhatsAppBotService:
    return WhatsAppBotService(
        conversation_repository=conversations,
        authorization_service=FakeAuthorizationService(authorization),
        form_service=FakeFormService(forms),
        attendance_repository=attendances,
        storage=storage,
        activity_service=activities,
    )


@pytest.fixture
def project_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def authorization(project_id: uuid.UUID) -> FakeAuthorization:
    return FakeAuthorization(id=uuid.uuid4(), name="João Teste", project_id=project_id)


@pytest.fixture
def simple_form(project_id: uuid.UUID):
    return make_form(
        id="form-1",
        name="Vistoria",
        project_id=str(project_id),
        fields=[
            FormField(id="nome", type=FieldType.TEXT, label="Nome", required=True, order=0),
            FormField(
                id="status",
                type=FieldType.SELECT,
                label="Status",
                required=True,
                order=1,
                options=[
                    FormFieldOption(id="opt1", label="Aprovado", value="aprovado"),
                    FormFieldOption(id="opt2", label="Reprovado", value="reprovado"),
                ],
            ),
        ],
    )


class TestAuthorization:
    async def test_unauthorized_phone_is_rejected(
        self, fake_conversations, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, None, [], fake_attendances, fake_storage, fake_activities)
        reply = await service.handle_message(_msg(text="oi"))
        assert "não está autorizado" in reply
        assert await fake_conversations.get_by_phone("5511999990000") is None


class TestFormSelection:
    async def test_first_message_greets_and_lists_published_forms(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        reply = await service.handle_message(_msg(text="oi"))
        assert authorization.name in reply
        assert simple_form.name in reply

        conversation = await fake_conversations.get_by_phone("5511999990000")
        assert conversation is not None
        assert conversation.state == ConversationState.AWAITING_FORM_SELECTION
        assert conversation.pending_options == [simple_form.id]

    async def test_invalid_form_selection_reprompts(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await service.handle_message(_msg(text="oi"))
        reply = await service.handle_message(_msg(text="99"))
        assert "não entendi" in reply.lower()

        conversation = await fake_conversations.get_by_phone("5511999990000")
        assert conversation.state == ConversationState.AWAITING_FORM_SELECTION

    async def test_valid_form_selection_asks_first_question(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await service.handle_message(_msg(text="oi"))
        reply = await service.handle_message(_msg(text="1"))
        assert "Nome" in reply

        conversation = await fake_conversations.get_by_phone("5511999990000")
        assert conversation.state == ConversationState.ANSWERING
        assert conversation.form_id == simple_form.id
        assert conversation.current_field_index == 0


class TestAnswering:
    async def _start_and_select_form(self, service) -> None:
        await service.handle_message(_msg(text="oi"))
        await service.handle_message(_msg(text="1"))

    async def test_text_answer_advances_to_next_field(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await self._start_and_select_form(service)

        reply = await service.handle_message(_msg(text="Maria Souza"))
        assert "Status" in reply

        conversation = await fake_conversations.get_by_phone("5511999990000")
        assert conversation.current_field_index == 1
        assert conversation.text_answers[0].value == "Maria Souza"

    async def test_select_field_invalid_index_reprompts_same_field(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await self._start_and_select_form(service)
        await service.handle_message(_msg(text="Maria Souza"))

        reply = await service.handle_message(_msg(text="9"))
        assert "opções" in reply.lower()

        conversation = await fake_conversations.get_by_phone("5511999990000")
        assert conversation.current_field_index == 1  # unchanged — still on the SELECT field

    async def test_select_field_valid_index_resolves_to_option_value(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await self._start_and_select_form(service)
        await service.handle_message(_msg(text="Maria Souza"))

        reply = await service.handle_message(_msg(text="1"))
        assert "Confirma" in reply

        conversation = await fake_conversations.get_by_phone("5511999990000")
        assert conversation.state == ConversationState.AWAITING_CONFIRMATION
        assert conversation.text_answers[1].value == "aprovado"  # resolved from option index, not the raw "1"

    async def test_required_field_cannot_be_skipped(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await self._start_and_select_form(service)

        reply = await service.handle_message(_msg(text="pular"))
        assert "obrigatório" in reply.lower()

        conversation = await fake_conversations.get_by_phone("5511999990000")
        assert conversation.current_field_index == 0  # unchanged

    async def test_optional_field_can_be_skipped(
        self, fake_conversations, authorization, project_id, fake_attendances, fake_storage, fake_activities
    ):
        form = make_form(
            id="form-2",
            project_id=str(project_id),
            fields=[
                FormField(id="nome", type=FieldType.TEXT, label="Nome", required=True, order=0),
                FormField(id="obs", type=FieldType.TEXTAREA, label="Observações", required=False, order=1),
            ],
        )
        service = _service(fake_conversations, authorization, [form], fake_attendances, fake_storage, fake_activities)
        await service.handle_message(_msg(text="oi"))
        await service.handle_message(_msg(text="1"))
        await service.handle_message(_msg(text="Maria Souza"))

        reply = await service.handle_message(_msg(text="pular"))
        assert "Confirma" in reply

        conversation = await fake_conversations.get_by_phone("5511999990000")
        assert len(conversation.text_answers) == 1  # the skipped field was never recorded


class TestConfirmation:
    async def _reach_confirmation(self, service) -> None:
        await service.handle_message(_msg(text="oi"))
        await service.handle_message(_msg(text="1"))
        await service.handle_message(_msg(text="Maria Souza"))
        await service.handle_message(_msg(text="1"))

    async def test_confirming_creates_attendance_and_clears_conversation(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await self._reach_confirmation(service)

        reply = await service.handle_message(_msg(text="sim"))
        assert "sucesso" in reply.lower()

        assert len(fake_attendances.created) == 1
        created = fake_attendances.created[0]
        assert created.form_id == simple_form.id
        assert created.operator_name == authorization.name
        assert {r.field_id: r.value for r in created.responses} == {"nome": "Maria Souza", "status": "aprovado"}

        assert await fake_conversations.get_by_phone("5511999990000") is None
        assert len(fake_activities.logged) == 1

    async def test_declining_discards_and_clears_conversation(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await self._reach_confirmation(service)

        reply = await service.handle_message(_msg(text="não"))
        assert "descartadas" in reply.lower()

        assert fake_attendances.created == []
        assert await fake_conversations.get_by_phone("5511999990000") is None

    async def test_unrecognized_confirmation_reprompts(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await self._reach_confirmation(service)

        reply = await service.handle_message(_msg(text="talvez"))
        assert "sim" in reply.lower() and "não" in reply.lower()
        assert fake_attendances.created == []
        assert await fake_conversations.get_by_phone("5511999990000") is not None


class TestCancelAndTimeout:
    async def test_cancel_mid_flow_resets_conversation(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await service.handle_message(_msg(text="oi"))
        await service.handle_message(_msg(text="1"))

        reply = await service.handle_message(_msg(text="cancelar"))
        assert "cancelada" in reply.lower()
        assert await fake_conversations.get_by_phone("5511999990000") is None

    async def test_stale_conversation_expires_and_restarts(
        self, fake_conversations, authorization, simple_form, fake_attendances, fake_storage, fake_activities
    ):
        service = _service(fake_conversations, authorization, [simple_form], fake_attendances, fake_storage, fake_activities)
        await service.handle_message(_msg(text="oi"))
        await service.handle_message(_msg(text="1"))

        conversation = await fake_conversations.get_by_phone("5511999990000")
        conversation.updated_at = datetime.now(timezone.utc) - timedelta(hours=25)

        reply = await service.handle_message(_msg(text="Maria Souza"))
        assert "expirou" in reply.lower()

        # Treated as a fresh start — "Maria Souza" was never consumed as an
        # answer, the reply is the form-selection greeting, not the next question.
        restarted = await fake_conversations.get_by_phone("5511999990000")
        assert restarted.state == ConversationState.AWAITING_FORM_SELECTION
