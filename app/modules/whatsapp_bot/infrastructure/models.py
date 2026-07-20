import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WhatsAppConversationModel(Base):
    __tablename__ = "whatsapp_conversations"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    authorization_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("whatsapp_authorizations.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    form_id: Mapped[str | None] = mapped_column(String(24))
    current_field_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_options: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    text_answers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    photo_answers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
