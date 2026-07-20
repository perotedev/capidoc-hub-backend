import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Header, UploadFile

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenancy import CurrentOrgProjectIds
from app.modules.auth.api.v1.dependencies import CurrentUser, require_permission
from app.modules.document_imports.api.v1.dependencies import DocumentImportServiceDep
from app.modules.document_imports.application.schemas import (
    DocumentImportCallbackRequest,
    DocumentImportConfirmRequest,
    DocumentImportConfirmResponse,
    DocumentImportResponse,
)
from app.shared.enums import PermissionOperation, Resource

router = APIRouter(prefix="/document-imports", tags=["Document Imports"])


@router.post(
    "",
    response_model=DocumentImportResponse,
    status_code=201,
    dependencies=[require_permission(Resource.ATENDIMENTO, PermissionOperation.CREATE)],
)
async def request_document_import(
    current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: DocumentImportServiceDep,
    form_id: Annotated[str, Form()],
    project_id: Annotated[uuid.UUID, Form()],
    file: UploadFile = File(...),
) -> DocumentImportResponse:
    if project_id not in org_project_ids:
        raise ForbiddenError("That project does not belong to your organization")
    content = await file.read()
    return await service.request_import(
        form_id=form_id,
        project_id=project_id,
        user_id=current_user.id,
        filename=file.filename or "document",
        content=content,
        content_type=file.content_type or "application/octet-stream",
    )


@router.get(
    "/{import_id}",
    response_model=DocumentImportResponse,
    dependencies=[require_permission(Resource.ATENDIMENTO, PermissionOperation.READ)],
)
async def get_document_import(
    import_id: UUID, _current_user: CurrentUser, org_project_ids: CurrentOrgProjectIds, service: DocumentImportServiceDep
) -> DocumentImportResponse:
    document_import = await service.get_import(import_id)
    if document_import.project_id not in org_project_ids:
        raise NotFoundError(f"Document import {import_id} not found")
    return document_import


@router.post("/{import_id}/callback", status_code=204)
async def document_import_callback(
    import_id: UUID,
    request: DocumentImportCallbackRequest,
    service: DocumentImportServiceDep,
    x_capidoc_secret: Annotated[str, Header(alias="X-CapiDoc-Secret")] = "",
) -> None:
    """Called by the n8n workflow once extraction finishes — authenticated by
    a shared secret header, not a user JWT (n8n isn't a logged-in user)."""
    await service.handle_callback(import_id, x_capidoc_secret, request)


@router.post(
    "/{import_id}/confirm",
    response_model=DocumentImportConfirmResponse,
    dependencies=[require_permission(Resource.ATENDIMENTO, PermissionOperation.CREATE)],
)
async def confirm_document_import(
    import_id: UUID,
    request: DocumentImportConfirmRequest,
    current_user: CurrentUser,
    org_project_ids: CurrentOrgProjectIds,
    service: DocumentImportServiceDep,
) -> DocumentImportConfirmResponse:
    document_import = await service.get_import(import_id)
    if document_import.project_id not in org_project_ids:
        raise NotFoundError(f"Document import {import_id} not found")
    return await service.confirm_import(import_id, current_user.id, current_user.name, request.responses)
