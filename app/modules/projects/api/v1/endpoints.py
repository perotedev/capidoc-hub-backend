from uuid import UUID

from fastapi import APIRouter, Query

from app.core.tenancy import CurrentOrgId
from app.modules.auth.api.v1.dependencies import CurrentUser
from app.modules.projects.api.v1.dependencies import ProjectServiceDep
from app.modules.projects.application.schemas import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=list[ProjectResponse])
async def search_projects(
    _current_user: CurrentUser,
    org_id: CurrentOrgId,
    service: ProjectServiceDep,
    query: str | None = Query(default=None),
) -> list[ProjectResponse]:
    summaries = await service.search(query, org_id)
    return [ProjectResponse.from_summary(summary) for summary in summaries]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID, _current_user: CurrentUser, org_id: CurrentOrgId, service: ProjectServiceDep
) -> ProjectResponse:
    summary = await service.get_project_summary(project_id, org_id)
    return ProjectResponse.from_summary(summary)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: ProjectCreateRequest, _current_user: CurrentUser, org_id: CurrentOrgId, service: ProjectServiceDep
) -> ProjectResponse:
    project = await service.create_project(request, org_id)
    summary = await service.get_project_summary(project.id, org_id)
    return ProjectResponse.from_summary(summary)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    request: ProjectUpdateRequest,
    _current_user: CurrentUser,
    org_id: CurrentOrgId,
    service: ProjectServiceDep,
) -> ProjectResponse:
    await service.update_project(project_id, request, org_id)
    summary = await service.get_project_summary(project_id, org_id)
    return ProjectResponse.from_summary(summary)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID, _current_user: CurrentUser, org_id: CurrentOrgId, service: ProjectServiceDep
) -> None:
    await service.delete_project(project_id, org_id)
