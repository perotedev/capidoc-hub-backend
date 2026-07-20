from uuid import UUID

from fastapi import APIRouter, Query

from app.modules.auth.api.v1.dependencies import CurrentUser
from app.modules.notifications.api.v1.dependencies import NotificationServiceDep
from app.modules.notifications.application.schemas import NotificationResponse, UnreadCountResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    current_user: CurrentUser,
    service: NotificationServiceDep,
    unread_only: bool = Query(default=False),
) -> list[NotificationResponse]:
    return await service.list_for_user(current_user.id, unread_only)


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(current_user: CurrentUser, service: NotificationServiceDep) -> UnreadCountResponse:
    count = await service.count_unread(current_user.id)
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", status_code=204)
async def mark_read(notification_id: UUID, current_user: CurrentUser, service: NotificationServiceDep) -> None:
    await service.mark_read(notification_id, current_user.id)


@router.post("/read-all", status_code=204)
async def mark_all_read(current_user: CurrentUser, service: NotificationServiceDep) -> None:
    await service.mark_all_read(current_user.id)
