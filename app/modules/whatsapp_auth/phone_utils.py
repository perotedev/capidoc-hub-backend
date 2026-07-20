import re


def normalize_phone_number(raw: str) -> str:
    """Strips WhatsApp JID suffixes (`@c.us`, `@s.whatsapp.net`) and any
    non-digit characters, so the same number always matches regardless of how
    WAHA or an admin happens to format it (with/without `+`, spaces, etc.)."""
    without_suffix = raw.split("@", 1)[0]
    return re.sub(r"\D", "", without_suffix)
