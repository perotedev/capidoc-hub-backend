import json
from uuid import UUID

from redis.asyncio import Redis

from app.modules.forms.domain.entities import FormEntity


def forms_channel(project_id: str | UUID) -> str:
    """Redis pub/sub channel backing the STOMP destination
    `/topic/projects/{project_id}/forms` — one channel per project."""
    return f"stomp:/topic/projects/{project_id}/forms"


async def publish_form_event(redis_client: Redis, event: str, form: FormEntity) -> None:
    """Fire-and-forget notification to any device subscribed to the form's
    project — used after publish/archive so an operator's device can refresh
    its form list immediately instead of waiting for its next manual sync."""
    payload = json.dumps(
        {"event": event, "formId": form.id, "formName": form.name, "status": form.status}
    )
    await redis_client.publish(forms_channel(form.project_id), payload)
