from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import Response

from app.modules.auth.api.v1.dependencies import CurrentUser
from app.modules.forms.api.v1.dependencies import FormServiceDep
from app.modules.forms.application.schemas import CreateFieldRequest, FormCreateRequest, FormRenameRequest
from app.modules.forms.domain.entities import FormEntity, FormField, FormSettings, FormStatus, TemplateBox

router = APIRouter(prefix="/forms", tags=["Forms"])


@router.get("", response_model=list[FormEntity])
async def search_forms(
    _current_user: CurrentUser,
    service: FormServiceDep,
    query: str | None = Query(default=None),
    status: FormStatus | None = Query(default=None),
    project_id: str | None = Query(default=None),
) -> list[FormEntity]:
    return await service.search(query, status, project_id)


@router.get("/{form_id}", response_model=FormEntity)
async def get_form(form_id: str, _current_user: CurrentUser, service: FormServiceDep) -> FormEntity:
    return await service.get_form(form_id)


@router.post("", response_model=FormEntity, status_code=201)
async def create_form(request: FormCreateRequest, current_user: CurrentUser, service: FormServiceDep) -> FormEntity:
    return await service.create_form(request, str(current_user.id), current_user.name)


@router.put("/{form_id}/rename", response_model=FormEntity)
async def rename_form(
    form_id: str, request: FormRenameRequest, _current_user: CurrentUser, service: FormServiceDep
) -> FormEntity:
    await service.rename_form(form_id, request)
    return await service.get_form(form_id)


@router.post("/{form_id}/fields", response_model=FormField, status_code=201)
async def add_field(
    form_id: str, request: CreateFieldRequest, _current_user: CurrentUser, service: FormServiceDep
) -> FormField:
    return await service.add_field(form_id, request)


@router.put("/{form_id}/fields", response_model=FormEntity)
async def update_fields(
    form_id: str, fields: list[FormField], _current_user: CurrentUser, service: FormServiceDep
) -> FormEntity:
    await service.update_fields(form_id, fields)
    return await service.get_form(form_id)


@router.put("/{form_id}/settings", response_model=FormEntity)
async def update_settings(
    form_id: str, settings: FormSettings, _current_user: CurrentUser, service: FormServiceDep
) -> FormEntity:
    await service.update_settings(form_id, settings)
    return await service.get_form(form_id)


@router.put("/{form_id}/template", response_model=FormEntity)
async def update_template(
    form_id: str, template: list[TemplateBox], _current_user: CurrentUser, service: FormServiceDep
) -> FormEntity:
    await service.update_template(form_id, template)
    return await service.get_form(form_id)


@router.put("/{form_id}/template-pdf", response_model=FormEntity)
async def upload_template_pdf(
    form_id: str,
    _current_user: CurrentUser,
    service: FormServiceDep,
    file: UploadFile = File(...),
) -> FormEntity:
    content = await file.read()
    return await service.upload_template_pdf(form_id, content)


@router.get("/{form_id}/template-pdf")
async def get_template_pdf(form_id: str, _current_user: CurrentUser, service: FormServiceDep) -> Response:
    content = await service.get_template_pdf(form_id)
    return Response(content=content, media_type="application/pdf")


@router.post("/{form_id}/publish", response_model=FormEntity)
async def publish_form(form_id: str, _current_user: CurrentUser, service: FormServiceDep) -> FormEntity:
    await service.publish(form_id)
    return await service.get_form(form_id)


@router.post("/{form_id}/archive", response_model=FormEntity)
async def archive_form(form_id: str, _current_user: CurrentUser, service: FormServiceDep) -> FormEntity:
    await service.archive(form_id)
    return await service.get_form(form_id)


@router.post("/{form_id}/duplicate", response_model=FormEntity, status_code=201)
async def duplicate_form(form_id: str, current_user: CurrentUser, service: FormServiceDep) -> FormEntity:
    return await service.duplicate(form_id, str(current_user.id), current_user.name)


@router.delete("/{form_id}", status_code=204)
async def delete_form(form_id: str, _current_user: CurrentUser, service: FormServiceDep) -> None:
    await service.delete_form(form_id)
