"""The WhatsApp bot's conversation state machine.

n8n only relays messages (WAHA webhook -> this service -> reply text -> WAHA
send). Every decision — which question to ask, how to validate an answer,
when to create the attendance — lives here, the same place as every other
form-domain rule in the app.
"""

import base64
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.storage import StorageService
from app.modules.activities.application.services import ActivityService
from app.modules.activities.domain.entities import ActivityType
from app.modules.attendances.domain.entities import AttendanceEntity, AttendancePhoto, AttendanceResponse
from app.modules.attendances.domain.repositories import AttendanceRepository
from app.modules.forms.application.services import FormService
from app.modules.forms.domain.entities import FieldType, FormEntity, FormField, FormStatus
from app.modules.whatsapp_auth.application.services import WhatsAppAuthorizationService
from app.modules.whatsapp_auth.domain.entities import WhatsAppAuthorizationEntity
from app.modules.whatsapp_auth.phone_utils import normalize_phone_number
from app.modules.whatsapp_bot.application.schemas import WhatsAppIncomingMessageRequest
from app.modules.whatsapp_bot.domain.entities import (
    ConversationState,
    WhatsAppConversationEntity,
    WhatsAppPhotoAnswer,
    WhatsAppTextAnswer,
)
from app.modules.whatsapp_bot.domain.repositories import WhatsAppConversationRepository

logger = logging.getLogger(__name__)

_UNSUPPORTED_FIELD_TYPES = {FieldType.SIGNATURE}  # everything else, incl. PHOTO/GPS, is supported over chat
_CONVERSATION_TIMEOUT = timedelta(hours=24)
_CANCEL_WORDS = {"cancelar", "cancel"}
_SKIP_WORDS = {"pular", "skip"}
_YES_WORDS = {"sim", "s", "yes", "y"}
_NO_WORDS = {"não", "nao", "n", "no"}


def _bot_fields(form: FormEntity) -> list[FormField]:
    return sorted((field for field in form.fields if field.type not in _UNSUPPORTED_FIELD_TYPES), key=lambda f: f.order)


def _build_question(field: FormField) -> tuple[str, list[str]]:
    """Returns (prompt text, pending_options) — `pending_options` is the
    ordered list of option *values* for menu-driven types, used to map the
    user's numeric reply back to a real value; empty for everything else."""
    label = field.label or field.id
    note = "" if field.required else " (opcional — responda 'pular' para pular)"

    if field.type in (FieldType.SELECT, FieldType.RADIO):
        menu = "\n".join(f"{index + 1}. {option.label}" for index, option in enumerate(field.options))
        return f"{label}{note}\n{menu}\n\nResponda com o número da opção.", [option.value for option in field.options]
    if field.type == FieldType.MULTI_SELECT:
        menu = "\n".join(f"{index + 1}. {option.label}" for index, option in enumerate(field.options))
        return (
            f"{label}{note}\n{menu}\n\nResponda com os números separados por vírgula (ex: 1,3).",
            [option.value for option in field.options],
        )
    if field.type == FieldType.CHECKBOX:
        return f"{label}{note}\nResponda 'sim' ou 'não'.", []
    if field.type == FieldType.PHOTO:
        return f"{label}{note}\nEnvie uma foto.", []
    if field.type == FieldType.GPS:
        return f"{label}{note}\nCompartilhe sua localização (clipe -> Localização).", []
    if field.type == FieldType.DATE:
        return f"{label}{note}\nResponda com a data (ex: 18/07/2026).", []
    if field.type == FieldType.TIME:
        return f"{label}{note}\nResponda com o horário (ex: 14:30).", []
    if field.type == FieldType.DATETIME:
        return f"{label}{note}\nResponda com data e horário (ex: 18/07/2026 14:30).", []
    if field.type == FieldType.NUMBER:
        return f"{label}{note}\nResponda com um número.", []
    if field.type == FieldType.CURRENCY:
        return f"{label}{note}\nResponda com o valor (ex: 150.00).", []
    return f"{label}{note}", []


class WhatsAppBotService:
    def __init__(
        self,
        conversation_repository: WhatsAppConversationRepository,
        authorization_service: WhatsAppAuthorizationService,
        form_service: FormService,
        attendance_repository: AttendanceRepository,
        storage: StorageService,
        activity_service: ActivityService,
    ) -> None:
        self._conversations = conversation_repository
        self._authorizations = authorization_service
        self._forms = form_service
        self._attendances = attendance_repository
        self._storage = storage
        self._activity_service = activity_service

    async def handle_message(self, request: WhatsAppIncomingMessageRequest) -> str:
        phone_number = normalize_phone_number(request.phone_number)
        text = (request.text or "").strip()
        text_lower = text.lower()

        authorization = await self._authorizations.get_active_by_phone(phone_number)
        if authorization is None:
            return "Este número não está autorizado a usar este canal. Entre em contato com o administrador."

        conversation = await self._conversations.get_by_phone(phone_number)

        expired = conversation is not None and self._is_stale(conversation)
        if expired:
            await self._conversations.delete_by_phone(phone_number)
            conversation = None

        if conversation is not None and text_lower in _CANCEL_WORDS:
            await self._conversations.delete_by_phone(phone_number)
            return "Operação cancelada. Envie qualquer mensagem para começar novamente."

        if conversation is None:
            reply = await self._start_conversation(phone_number, authorization)
            if expired:
                return "Sua sessão anterior expirou por inatividade.\n\n" + reply
            return reply

        if conversation.state == ConversationState.AWAITING_FORM_SELECTION:
            return await self._handle_form_selection(conversation, text)

        if conversation.state == ConversationState.ANSWERING:
            return await self._handle_answer(conversation, request, text, text_lower)

        return await self._handle_confirmation(conversation, text_lower)

    async def _start_conversation(self, phone_number: str, authorization: WhatsAppAuthorizationEntity) -> str:
        forms = await self._forms.search(None, FormStatus.PUBLISHED, str(authorization.project_id))
        if not forms:
            return f"Olá, {authorization.name}! Não há formulários disponíveis no momento."

        conversation = WhatsAppConversationEntity(
            id=uuid.uuid4(),
            phone_number=phone_number,
            authorization_id=authorization.id,
            state=ConversationState.AWAITING_FORM_SELECTION,
            form_id=None,
            current_field_index=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            pending_options=[form.id for form in forms],
        )
        await self._conversations.create(conversation)

        menu = "\n".join(f"{index + 1}. {form.name}" for index, form in enumerate(forms))
        return f"Olá, {authorization.name}! Escolha o formulário que deseja responder:\n{menu}"

    async def _handle_form_selection(self, conversation: WhatsAppConversationEntity, text: str) -> str:
        index = self._parse_menu_index(text, len(conversation.pending_options))
        if index is None:
            return "Não entendi. Responda com o número do formulário desejado."

        form_id = conversation.pending_options[index]
        form = await self._forms.get_form(form_id)
        fields = _bot_fields(form)

        conversation.form_id = form_id
        conversation.current_field_index = 0
        conversation.text_answers = []
        conversation.photo_answers = []

        if not fields:
            conversation.state = ConversationState.AWAITING_CONFIRMATION
            conversation.pending_options = []
            await self._conversations.update(conversation)
            return self._build_confirmation_message(form.name, conversation)

        conversation.state = ConversationState.ANSWERING
        prompt, pending_options = _build_question(fields[0])
        conversation.pending_options = pending_options
        await self._conversations.update(conversation)
        return f"Formulário: {form.name}\n\n{prompt}"

    async def _handle_answer(
        self, conversation: WhatsAppConversationEntity, request: WhatsAppIncomingMessageRequest, text: str, text_lower: str
    ) -> str:
        assert conversation.form_id is not None
        form = await self._forms.get_form(conversation.form_id)
        fields = _bot_fields(form)
        field = fields[conversation.current_field_index]

        if text_lower in _SKIP_WORDS:
            if field.required:
                return "Este campo é obrigatório."
            # leave both answers untouched — field is simply omitted
        else:
            error = await self._store_answer(conversation, field, request, text, text_lower)
            if error is not None:
                return error

        conversation.current_field_index += 1
        if conversation.current_field_index >= len(fields):
            conversation.state = ConversationState.AWAITING_CONFIRMATION
            conversation.pending_options = []
            await self._conversations.update(conversation)
            return self._build_confirmation_message(form.name, conversation)

        next_field = fields[conversation.current_field_index]
        prompt, pending_options = _build_question(next_field)
        conversation.pending_options = pending_options
        await self._conversations.update(conversation)
        return prompt

    async def _store_answer(
        self,
        conversation: WhatsAppConversationEntity,
        field: FormField,
        request: WhatsAppIncomingMessageRequest,
        text: str,
        text_lower: str,
    ) -> str | None:
        """Validates + stores one answer onto `conversation` in place.
        Returns an error message to send back (re-prompting) on failure, or
        `None` on success."""

        if field.type in (FieldType.SELECT, FieldType.RADIO):
            index = self._parse_menu_index(text, len(conversation.pending_options))
            if index is None:
                return "Responda com o número de uma das opções acima."
            conversation.text_answers.append(
                WhatsAppTextAnswer(field.id, field.label, conversation.pending_options[index])
            )
            return None

        if field.type == FieldType.MULTI_SELECT:
            indices = self._parse_menu_indices(text, len(conversation.pending_options))
            if not indices:
                return "Responda com os números das opções desejadas, separados por vírgula."
            values = [conversation.pending_options[i] for i in indices]
            conversation.text_answers.append(WhatsAppTextAnswer(field.id, field.label, ", ".join(values)))
            return None

        if field.type == FieldType.CHECKBOX:
            if text_lower in _YES_WORDS:
                conversation.text_answers.append(WhatsAppTextAnswer(field.id, field.label, "true"))
                return None
            if text_lower in _NO_WORDS:
                conversation.text_answers.append(WhatsAppTextAnswer(field.id, field.label, "false"))
                return None
            return "Responda 'sim' ou 'não'."

        if field.type == FieldType.PHOTO:
            if not request.media_base64:
                return "Envie uma foto para continuar."
            file_key = await self._store_photo(conversation, request)
            conversation.photo_answers.append(WhatsAppPhotoAnswer(field.id, field.label, file_key))
            return None

        if field.type == FieldType.GPS:
            if request.latitude is None or request.longitude is None:
                return "Compartilhe sua localização para continuar."
            gps_value = json.dumps({"latitude": request.latitude, "longitude": request.longitude, "accuracy": 0})
            conversation.text_answers.append(WhatsAppTextAnswer(field.id, field.label, gps_value))
            return None

        if field.type == FieldType.NUMBER:
            try:
                float(text.replace(",", "."))
            except ValueError:
                return "Não entendi. Responda com um número."
            conversation.text_answers.append(WhatsAppTextAnswer(field.id, field.label, text))
            return None

        # TEXT, TEXTAREA, CURRENCY, DATE, TIME, DATETIME — free text
        if not text:
            return "Este campo é obrigatório." if field.required else "Não entendi sua resposta."
        conversation.text_answers.append(WhatsAppTextAnswer(field.id, field.label, text))
        return None

    async def _store_photo(self, conversation: WhatsAppConversationEntity, request: WhatsAppIncomingMessageRequest) -> str:
        assert request.media_base64 is not None
        content = base64.b64decode(request.media_base64)
        extension = (request.media_mime_type or "image/jpeg").split("/")[-1]
        file_key = f"whatsapp-bot/{conversation.phone_number}/{uuid.uuid4()}.{extension}"
        await self._storage.upload_file(file_key, content, request.media_mime_type or "image/jpeg")
        return file_key

    def _build_confirmation_message(self, form_name: str, conversation: WhatsAppConversationEntity) -> str:
        lines = [f"Confira suas respostas para \"{form_name}\":"]
        for answer in conversation.text_answers:
            lines.append(f"- {answer.field_label or answer.field_id}: {answer.value}")
        for photo in conversation.photo_answers:
            lines.append(f"- {photo.caption or photo.field_id}: [foto enviada]")
        lines.append("\nConfirma o envio? (sim/não)")
        return "\n".join(lines)

    async def _handle_confirmation(self, conversation: WhatsAppConversationEntity, text_lower: str) -> str:
        if text_lower in _NO_WORDS:
            await self._conversations.delete_by_phone(conversation.phone_number)
            return "Ok, respostas descartadas. Envie qualquer mensagem para começar novamente."

        if text_lower not in _YES_WORDS:
            return "Responda 'sim' para confirmar ou 'não' para descartar."

        assert conversation.form_id is not None
        try:
            await self._create_attendance(conversation)
        except Exception:
            logger.exception("Failed to create attendance from WhatsApp conversation %s", conversation.id)
            await self._conversations.delete_by_phone(conversation.phone_number)
            return "Ocorreu um erro ao registrar suas respostas. Por favor, comece novamente."

        await self._conversations.delete_by_phone(conversation.phone_number)
        return "Atendimento registrado com sucesso! Obrigado. Envie qualquer mensagem para responder outro formulário."

    async def _create_attendance(self, conversation: WhatsAppConversationEntity) -> None:
        assert conversation.form_id is not None
        form = await self._forms.get_form(conversation.form_id)
        authorization = await self._authorizations.get(conversation.authorization_id)

        now = datetime.now(timezone.utc)
        attendance = AttendanceEntity(
            id="",
            form_id=form.id,
            form_name=form.name,
            operator_id=str(authorization.id),
            operator_name=authorization.name,
            project_id=str(authorization.project_id),
            project_name=authorization.project_name,
            duration=0,
            responses=[
                AttendanceResponse(field_id=answer.field_id, field_label=answer.field_label, value=answer.value)
                for answer in conversation.text_answers
            ],
            photos=[
                AttendancePhoto(id=str(uuid.uuid4()), field_id=photo.field_id, caption=photo.caption, file_key=photo.file_key)
                for photo in conversation.photo_answers
            ],
            signature=False,
            gps_location=None,
            created_at=now,
            completed_at=now,
            synced_at=now,
        )
        await self._attendances.create(attendance)
        await self._forms.notify_attendance_submitted(form.id)
        await self._activity_service.log_for_project(
            authorization.project_id,
            ActivityType.ATTENDANCE,
            "Atendimento registrado",
            f'{authorization.name} respondeu "{form.name}" via WhatsApp',
            "message-circle",
            None,
            authorization.name,
        )

    @staticmethod
    def _is_stale(conversation: WhatsAppConversationEntity) -> bool:
        return datetime.now(timezone.utc) - conversation.updated_at > _CONVERSATION_TIMEOUT

    @staticmethod
    def _parse_menu_index(text: str, option_count: int) -> int | None:
        try:
            index = int(text.strip()) - 1
        except ValueError:
            return None
        return index if 0 <= index < option_count else None

    @staticmethod
    def _parse_menu_indices(text: str, option_count: int) -> list[int]:
        raw_parts = [part.strip() for part in text.replace(" ", ",").split(",") if part.strip()]
        indices: list[int] = []
        for part in raw_parts:
            try:
                index = int(part) - 1
            except ValueError:
                continue
            if 0 <= index < option_count and index not in indices:
                indices.append(index)
        return indices
