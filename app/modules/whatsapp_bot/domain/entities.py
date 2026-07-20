from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ConversationState(StrEnum):
    AWAITING_FORM_SELECTION = "awaiting_form_selection"
    ANSWERING = "answering"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


@dataclass(slots=True)
class WhatsAppTextAnswer:
    field_id: str
    field_label: str
    value: str


@dataclass(slots=True)
class WhatsAppPhotoAnswer:
    field_id: str
    caption: str
    file_key: str


@dataclass(slots=True)
class WhatsAppConversationEntity:
    id: UUID
    phone_number: str
    authorization_id: UUID
    state: ConversationState
    form_id: str | None
    current_field_index: int
    created_at: datetime
    updated_at: datetime
    pending_options: list[str] = field(default_factory=list)
    text_answers: list[WhatsAppTextAnswer] = field(default_factory=list)
    photo_answers: list[WhatsAppPhotoAnswer] = field(default_factory=list)
