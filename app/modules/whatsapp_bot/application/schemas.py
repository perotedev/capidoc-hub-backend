from app.shared.schema import CamelCaseModel


class WhatsAppIncomingMessageRequest(CamelCaseModel):
    """What n8n posts for every inbound WhatsApp message it relays from WAHA.

    n8n is responsible for mapping WAHA's own webhook payload into this
    shape: `text` for a plain text reply, `media_base64`/`media_mime_type`
    when the user sent an image (n8n fetches it from WAHA and base64-encodes
    it — this backend has no WAHA credentials), or `latitude`/`longitude`
    when the user shared their location."""

    phone_number: str
    text: str | None = None
    media_base64: str | None = None
    media_mime_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class WhatsAppBotReplyResponse(CamelCaseModel):
    reply_text: str
