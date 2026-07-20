from typing import Annotated

from fastapi import APIRouter, Header

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.modules.whatsapp_bot.api.v1.dependencies import WhatsAppBotServiceDep
from app.modules.whatsapp_bot.application.schemas import WhatsAppBotReplyResponse, WhatsAppIncomingMessageRequest

settings = get_settings()

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Bot"])


@router.post("/messages", response_model=WhatsAppBotReplyResponse)
async def handle_incoming_message(
    request: WhatsAppIncomingMessageRequest,
    service: WhatsAppBotServiceDep,
    x_capidoc_secret: Annotated[str, Header(alias="X-CapiDoc-Secret")] = "",
) -> WhatsAppBotReplyResponse:
    """Called by the n8n relay for every inbound WhatsApp message — n8n owns
    the WAHA connection; this endpoint only decides what to reply. Protected
    by a shared secret, not a user JWT (n8n isn't a logged-in user)."""
    if x_capidoc_secret != settings.whatsapp_webhook_secret:
        raise UnauthorizedError("Invalid webhook secret")
    reply_text = await service.handle_message(request)
    return WhatsAppBotReplyResponse(reply_text=reply_text)
