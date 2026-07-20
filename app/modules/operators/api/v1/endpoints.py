from uuid import UUID

from fastapi import APIRouter, Query

from app.modules.auth.api.v1.dependencies import CurrentUser
from app.modules.operators.api.v1.dependencies import OperatorServiceDep
from app.modules.operators.application.schemas import OperatorResponse

router = APIRouter(prefix="/operators", tags=["Operators"])


@router.get("", response_model=list[OperatorResponse])
async def list_operators(
    _current_user: CurrentUser,
    service: OperatorServiceDep,
    project_id: UUID | None = Query(default=None),
) -> list[OperatorResponse]:
    reports = await service.list_operators(project_id)
    return [OperatorResponse.from_entity(report) for report in reports]


@router.get("/{operator_id}", response_model=OperatorResponse)
async def get_operator(
    operator_id: UUID, _current_user: CurrentUser, service: OperatorServiceDep
) -> OperatorResponse:
    report = await service.get_operator(operator_id)
    return OperatorResponse.from_entity(report)
