from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile

from app.modules.activities.api.v1.dependencies import ActivityServiceDep
from app.modules.activities.domain.entities import ActivityType
from app.modules.auth.api.v1.dependencies import CurrentUser
from app.modules.documents.api.v1.dependencies import DocumentServiceDep, DocumentTemplateServiceDep
from app.modules.documents.application.schemas import (
    DocumentGenerateRequest,
    DocumentResponse,
    DocumentRevokeRequest,
    DocumentTemplateCreateRequest,
    DocumentTemplateResponse,
    DocumentTemplateUpdateRequest,
)
from app.modules.documents.domain.entities import DocStatus

router = APIRouter(prefix="/documents", tags=["Documents"])
templates_router = APIRouter(prefix="/document-templates", tags=["Document Templates"])


@router.get("", response_model=list[DocumentResponse])
async def search_documents(
    _current_user: CurrentUser,
    service: DocumentServiceDep,
    query: str | None = Query(default=None),
    status: DocStatus | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[DocumentResponse]:
    return await service.search(query, status, project_id)


@router.get("/by-attendance/{attendance_id}", response_model=DocumentResponse)
async def get_document_by_attendance(
    attendance_id: str, _current_user: CurrentUser, service: DocumentServiceDep
) -> DocumentResponse:
    return await service.get_by_attendance(attendance_id)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID, _current_user: CurrentUser, service: DocumentServiceDep) -> DocumentResponse:
    return await service.get_document(document_id)


@router.post("", response_model=DocumentResponse, status_code=201)
async def register_document(
    request: DocumentGenerateRequest, current_user: CurrentUser, service: DocumentServiceDep, activity_service: ActivityServiceDep
) -> DocumentResponse:
    document = await service.register_document(request)
    if document.status == DocStatus.GENERATED:
        await activity_service.log_for_project(
            document.project_id,
            ActivityType.DOCUMENT,
            "Documento gerado",
            f'Documento de "{document.form_name}" gerado para {document.operator_name}',
            "file-check",
            current_user.id,
            current_user.name,
        )
    return document


@router.post("/{document_id}/pdf", response_model=DocumentResponse)
async def upload_document_pdf(
    document_id: UUID,
    current_user: CurrentUser,
    service: DocumentServiceDep,
    activity_service: ActivityServiceDep,
    file: UploadFile = File(...),
) -> DocumentResponse:
    content = await file.read()
    document = await service.upload_generated_pdf(document_id, content)
    await activity_service.log_for_project(
        document.project_id,
        ActivityType.DOCUMENT,
        "Documento gerado",
        f'Documento de "{document.form_name}" gerado para {document.operator_name}',
        "file-check",
        current_user.id,
        current_user.name,
    )
    return document


@router.post("/{document_id}/revoke", response_model=DocumentResponse)
async def revoke_document(
    document_id: UUID,
    request: DocumentRevokeRequest,
    current_user: CurrentUser,
    service: DocumentServiceDep,
) -> DocumentResponse:
    return await service.revoke_document(document_id, current_user.id, request.reason)


@templates_router.get("/project/{project_id}", response_model=list[DocumentTemplateResponse])
async def list_templates(
    project_id: UUID, _current_user: CurrentUser, service: DocumentTemplateServiceDep
) -> list[DocumentTemplateResponse]:
    return await service.list_by_project(project_id)


@templates_router.get("/{template_id}", response_model=DocumentTemplateResponse)
async def get_template(
    template_id: UUID, _current_user: CurrentUser, service: DocumentTemplateServiceDep
) -> DocumentTemplateResponse:
    return await service.get_template(template_id)


@templates_router.post("", response_model=DocumentTemplateResponse, status_code=201)
async def create_template(
    request: DocumentTemplateCreateRequest, _current_user: CurrentUser, service: DocumentTemplateServiceDep
) -> DocumentTemplateResponse:
    return await service.create_template(request)


@templates_router.patch("/{template_id}", response_model=DocumentTemplateResponse)
async def update_template(
    template_id: UUID,
    request: DocumentTemplateUpdateRequest,
    _current_user: CurrentUser,
    service: DocumentTemplateServiceDep,
) -> DocumentTemplateResponse:
    return await service.update_template(template_id, request)


@templates_router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: UUID, _current_user: CurrentUser, service: DocumentTemplateServiceDep
) -> None:
    await service.delete_template(template_id)
