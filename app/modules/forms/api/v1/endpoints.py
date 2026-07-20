from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from redis.asyncio import Redis

from app.core.exceptions import NotFoundError
from app.core.redis_client import get_redis_client
from app.core.tenancy import CurrentOrgProjectIds
from app.modules.activities.api.v1.dependencies import ActivityServiceDep
from app.modules.activities.domain.entities import ActivityType
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.modules.forms.api.v1.dependencies import FormServiceDep
from app.modules.forms.application.schemas import CreateFieldRequest, FormCreateRequest, FormRenameRequest
from app.modules.forms.domain.entities import FormEntity, FormField, FormSettings, FormStatus, TemplateBox
from app.modules.mobile.realtime import publish_form_event
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/forms", tags=["Forms"])


async def _assert_form_in_org(form: FormEntity, org_project_ids: list[UUID]) -> None:
    allowed = {str(project_id) for project_id in org_project_ids}
    if form.project_id not in allowed:
        raise NotFoundError(f"Form {form.id} not found")


@router.get("", response_model=list[FormEntity], dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.READ)])
async def search_forms(
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: FormServiceDep,
    query: str | None = Query(default=None),
    status: FormStatus | None = Query(default=None),
    project_id: str | None = Query(default=None),
) -> list[FormEntity]:
    allowed = {str(pid) for pid in org_project_ids}
    if project_id is not None and project_id not in allowed:
        return []
    forms = await service.search(query, status, project_id)
    return [form for form in forms if form.project_id in allowed]


@router.get("/{form_id}", response_model=FormEntity, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.READ)])
async def get_form(form_id: str, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: FormServiceDep) -> FormEntity:
    form = await service.get_form(form_id)
    await _assert_form_in_org(form, org_project_ids)
    return form


@router.post("", response_model=FormEntity, status_code=201, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.CREATE)])
async def create_form(
    request: FormCreateRequest, current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: FormServiceDep
) -> FormEntity:
    allowed = {str(pid) for pid in org_project_ids}
    if request.project_id not in allowed:
        raise NotFoundError("That project does not belong to your organization")
    return await service.create_form(request, str(current_user.id), current_user.name)


@router.put("/{form_id}/rename", response_model=FormEntity, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.UPDATE)])
async def rename_form(
    form_id: str, request: FormRenameRequest, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: FormServiceDep
) -> FormEntity:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    await service.rename_form(form_id, request)
    return await service.get_form(form_id)


@router.post("/{form_id}/fields", response_model=FormField, status_code=201, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.UPDATE)])
async def add_field(
    form_id: str, request: CreateFieldRequest, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: FormServiceDep
) -> FormField:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    return await service.add_field(form_id, request)


@router.put("/{form_id}/fields", response_model=FormEntity, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.UPDATE)])
async def update_fields(
    form_id: str, fields: list[FormField], _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: FormServiceDep
) -> FormEntity:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    await service.update_fields(form_id, fields)
    return await service.get_form(form_id)


@router.put("/{form_id}/settings", response_model=FormEntity, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.UPDATE)])
async def update_settings(
    form_id: str, settings: FormSettings, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: FormServiceDep
) -> FormEntity:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    await service.update_settings(form_id, settings)
    return await service.get_form(form_id)


@router.put("/{form_id}/template", response_model=FormEntity, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.UPDATE)])
async def update_template(
    form_id: str, template: list[TemplateBox], _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: FormServiceDep
) -> FormEntity:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    await service.update_template(form_id, template)
    return await service.get_form(form_id)


@router.put("/{form_id}/template-pdf", response_model=FormEntity, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.UPDATE)])
async def upload_template_pdf(
    form_id: str,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: FormServiceDep,
    file: UploadFile = File(...),
) -> FormEntity:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    content = await file.read()
    return await service.upload_template_pdf(form_id, content)


@router.get("/{form_id}/template-pdf", dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.READ)])
async def get_template_pdf(
    form_id: str, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: FormServiceDep
) -> Response:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    content = await service.get_template_pdf(form_id)
    return Response(content=content, media_type="application/pdf")


@router.post("/{form_id}/publish", response_model=FormEntity, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.UPDATE)])
async def publish_form(
    form_id: str,
    current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: FormServiceDep,
    redis_client: Annotated[Redis, Depends(get_redis_client)],
    activity_service: ActivityServiceDep,
) -> FormEntity:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    await service.publish(form_id)
    form = await service.get_form(form_id)
    await publish_form_event(redis_client, "published", form)
    await activity_service.log_for_project(
        UUID(form.project_id),
        ActivityType.FORM,
        "Formulário publicado",
        f'{current_user.name} publicou "{form.name}"',
        "file-text",
        current_user.id,
        current_user.name,
    )
    return form


@router.post("/{form_id}/archive", response_model=FormEntity, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.UPDATE)])
async def archive_form(
    form_id: str,
    _current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: FormServiceDep,
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> FormEntity:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    await service.archive(form_id)
    form = await service.get_form(form_id)
    await publish_form_event(redis_client, "archived", form)
    return form


@router.post("/{form_id}/duplicate", response_model=FormEntity, status_code=201, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.CREATE)])
async def duplicate_form(
    form_id: str, current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: FormServiceDep
) -> FormEntity:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    return await service.duplicate(form_id, str(current_user.id), current_user.name)


@router.delete("/{form_id}", status_code=204, dependencies=[require_permission(Resource.FORMULARIO, PermissionOperation.DELETE)])
async def delete_form(
    form_id: str, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: FormServiceDep
) -> None:
    await _assert_form_in_org(await service.get_form(form_id), org_project_ids)
    await service.delete_form(form_id)
