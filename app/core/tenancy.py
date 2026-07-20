from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.exceptions import ForbiddenError
from app.modules.auth.api.v1.dependencies import CurrentUser
from app.modules.organizations.api.v1.dependencies import get_organization_repository
from app.modules.organizations.domain.repositories import OrganizationRepository
from app.modules.projects.api.v1.dependencies import get_project_repository
from app.modules.projects.domain.repositories import ProjectRepository
from app.shared.enums import Role


async def get_current_org_id(
    current_user: CurrentUser,
    organization_repository: Annotated[OrganizationRepository, Depends(get_organization_repository)],
    project_repository: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> UUID:
    """Resolves the tenant (organization) the current request is scoped to.

    SUPER_ADMIN has no organization context at all — by design, they cannot
    reach tenant-scoped endpoints; ADMIN owns theirs directly; USER/AUDITOR
    inherit it through their assigned project.
    """
    if current_user.role == Role.SUPER_ADMIN:
        raise ForbiddenError("Super admins do not have an organization context")

    if current_user.role == Role.ADMIN:
        organization = await organization_repository.get_by_admin_id(current_user.id)
        if organization is None:
            raise ForbiddenError("No organization is associated with this admin account")
        return organization.id

    if current_user.project_id is None:
        raise ForbiddenError("This account is not assigned to a project")
    project = await project_repository.get_by_id(current_user.project_id)
    if project is None:
        raise ForbiddenError("Assigned project no longer exists")
    return project.org_id


CurrentOrgId = Annotated[UUID, Depends(get_current_org_id)]


async def get_current_org_project_ids(
    org_id: CurrentOrgId,
    project_repository: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> list[UUID]:
    """All project ids under the caller's organization — the scope every
    tenant-data query/mutation should be constrained to."""
    summaries = await project_repository.search(None, org_id)
    return [summary.project.id for summary in summaries]


CurrentOrgProjectIds = Annotated[list[UUID], Depends(get_current_org_project_ids)]
