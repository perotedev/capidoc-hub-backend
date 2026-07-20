from fastapi import APIRouter, Query

from app.core.tenancy import CurrentOrgId
from app.modules.activities.api.v1.dependencies import ActivityServiceDep
from app.modules.activities.application.schemas import ActivityResponse
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.get(
    "",
    response_model=list[ActivityResponse],
    dependencies=[require_permission(Resource.DASHBOARD, PermissionOperation.READ)],
)
async def list_recent_activities(
    _current_user: CurrentUser,
    org_id: CurrentOrgId,
    service: ActivityServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ActivityResponse]:
    return await service.list_recent(org_id, limit)
