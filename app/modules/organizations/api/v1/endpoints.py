from uuid import UUID

from fastapi import APIRouter

from app.modules.auth.api.v1.dependencies import CurrentUser, require_roles
from app.modules.organizations.api.v1.dependencies import OrganizationServiceDep
from app.modules.organizations.application.schemas import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
)
from app.shared.enums import Role

router = APIRouter(
    prefix="/organizations", tags=["Organizations"], dependencies=[require_roles(Role.SUPER_ADMIN)]
)


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(_current_user: CurrentUser, service: OrganizationServiceDep) -> list[OrganizationResponse]:
    summaries = await service.list_organizations()
    return [OrganizationResponse.from_summary(summary) for summary in summaries]


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID, _current_user: CurrentUser, service: OrganizationServiceDep
) -> OrganizationResponse:
    summary = await service.get_organization(organization_id)
    return OrganizationResponse.from_summary(summary)


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    request: OrganizationCreateRequest, _current_user: CurrentUser, service: OrganizationServiceDep
) -> OrganizationResponse:
    summary = await service.create_organization(request)
    return OrganizationResponse.from_summary(summary)


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    request: OrganizationUpdateRequest,
    _current_user: CurrentUser,
    service: OrganizationServiceDep,
) -> OrganizationResponse:
    summary = await service.update_organization(organization_id, request)
    return OrganizationResponse.from_summary(summary)
