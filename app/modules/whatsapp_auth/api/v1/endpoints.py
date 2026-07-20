from uuid import UUID

from fastapi import APIRouter, Query

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenancy import CurrentOrgProjectIds
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.modules.whatsapp_auth.api.v1.dependencies import WhatsAppAuthorizationServiceDep
from app.modules.whatsapp_auth.application.schemas import (
    WhatsAppAuthorizationCreateRequest,
    WhatsAppAuthorizationResponse,
    WhatsAppAuthorizationUpdateRequest,
)
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/whatsapp-authorizations", tags=["WhatsApp Authorizations"])


@router.get(
    "",
    response_model=list[WhatsAppAuthorizationResponse],
    dependencies=[require_permission(Resource.WHATSAPP, PermissionOperation.READ)],
)
async def search_authorizations(
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: WhatsAppAuthorizationServiceDep,
    query: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[WhatsAppAuthorizationResponse]:
    if project_id is not None:
        if project_id not in org_project_ids:
            raise ForbiddenError("That project does not belong to your organization")
        return await service.search(query, project_id)
    results = await service.search(query, None)
    allowed = set(org_project_ids)
    return [result for result in results if result.project_id in allowed]


@router.post(
    "",
    response_model=WhatsAppAuthorizationResponse,
    status_code=201,
    dependencies=[require_permission(Resource.WHATSAPP, PermissionOperation.CREATE)],
)
async def create_authorization(
    request: WhatsAppAuthorizationCreateRequest,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: WhatsAppAuthorizationServiceDep,
) -> WhatsAppAuthorizationResponse:
    if request.project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    return await service.create(request)


@router.put(
    "/{authorization_id}",
    response_model=WhatsAppAuthorizationResponse,
    dependencies=[require_permission(Resource.WHATSAPP, PermissionOperation.UPDATE)],
)
async def update_authorization(
    authorization_id: UUID,
    request: WhatsAppAuthorizationUpdateRequest,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: WhatsAppAuthorizationServiceDep,
) -> WhatsAppAuthorizationResponse:
    target = await service.get(authorization_id)
    if target.project_id not in org_project_ids:
        raise NotFoundError(f"WhatsApp authorization {authorization_id} not found")
    if request.project_id is not None and request.project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    return await service.update(authorization_id, request)


@router.post(
    "/{authorization_id}/revoke",
    response_model=WhatsAppAuthorizationResponse,
    dependencies=[require_permission(Resource.WHATSAPP, PermissionOperation.UPDATE)],
)
async def revoke_authorization(
    authorization_id: UUID,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: WhatsAppAuthorizationServiceDep,
) -> WhatsAppAuthorizationResponse:
    target = await service.get(authorization_id)
    if target.project_id not in org_project_ids:
        raise NotFoundError(f"WhatsApp authorization {authorization_id} not found")
    return await service.revoke(authorization_id)


@router.post(
    "/{authorization_id}/renew",
    response_model=WhatsAppAuthorizationResponse,
    dependencies=[require_permission(Resource.WHATSAPP, PermissionOperation.UPDATE)],
)
async def renew_authorization(
    authorization_id: UUID,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: WhatsAppAuthorizationServiceDep,
) -> WhatsAppAuthorizationResponse:
    target = await service.get(authorization_id)
    if target.project_id not in org_project_ids:
        raise NotFoundError(f"WhatsApp authorization {authorization_id} not found")
    return await service.renew(authorization_id)


@router.delete(
    "/{authorization_id}",
    status_code=204,
    dependencies=[require_permission(Resource.WHATSAPP, PermissionOperation.DELETE)],
)
async def delete_authorization(
    authorization_id: UUID,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: WhatsAppAuthorizationServiceDep,
) -> None:
    target = await service.get(authorization_id)
    if target.project_id not in org_project_ids:
        raise NotFoundError(f"WhatsApp authorization {authorization_id} not found")
    await service.delete(authorization_id)
