from uuid import UUID

from fastapi import APIRouter, Query

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenancy import CurrentOrgProjectIds
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.modules.operators.api.v1.dependencies import OperatorServiceDep
from app.modules.operators.application.schemas import OperatorResponse
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/operators", tags=["Operators"])


@router.get("", response_model=list[OperatorResponse], dependencies=[require_permission(Resource.OPERADOR, PermissionOperation.READ)])
async def list_operators(
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: OperatorServiceDep,
    project_id: UUID | None = Query(default=None),
) -> list[OperatorResponse]:
    if project_id is not None and project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    scope = [project_id] if project_id is not None else org_project_ids
    reports = await service.list_operators(scope)
    return [OperatorResponse.from_entity(report) for report in reports]


@router.get("/{operator_id}", response_model=OperatorResponse, dependencies=[require_permission(Resource.OPERADOR, PermissionOperation.READ)])
async def get_operator(
    operator_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: OperatorServiceDep
) -> OperatorResponse:
    report = await service.get_operator(operator_id)
    if report.project_id not in org_project_ids:
        raise NotFoundError(f"Operator {operator_id} not found")
    return OperatorResponse.from_entity(report)
