import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.storage import StorageService, get_storage_service
from app.core.tenancy import CurrentOrgId
from app.modules.attendances.api.v1.dependencies import AttendanceServiceDep
from app.modules.attendances.domain.entities import AttendanceEntity, AttendancePhoto, AttendanceResponse
from app.modules.auth.api.v1.dependencies import CurrentUser, require_roles
from app.modules.devices.api.v1.dependencies import DeviceServiceDep
from app.modules.devices.application.schemas import DeviceResponse
from app.modules.forms.api.v1.dependencies import FormServiceDep
from app.modules.forms.domain.entities import FieldType, FormEntity, FormStatus
from app.modules.mobile.application.schemas import AttendanceSubmitRequest, MobileDeviceRegisterRequest
from app.modules.projects.api.v1.dependencies import ProjectServiceDep
from app.shared.enums import Role

router = APIRouter(prefix="/mobile", tags=["Mobile"])


def _require_project_id(current_user: CurrentUser) -> uuid.UUID:
    """The mobile app is only meaningful for operators tied to a project — an
    ADMIN/SUPER_ADMIN/AUDITOR hitting these endpoints has nothing to fetch."""
    if current_user.project_id is None:
        raise BusinessRuleError("Your account is not assigned to a project yet")
    return current_user.project_id


@router.post("/devices/register", response_model=DeviceResponse, status_code=201)
async def register_device(
    request: MobileDeviceRegisterRequest,
    current_user: CurrentUser,
    device_service: DeviceServiceDep,
) -> DeviceResponse:
    project_id = _require_project_id(current_user)
    return await device_service.register_mobile_device(
        uid=request.uid,
        model=request.model,
        os_version=request.os_version,
        app_version=request.app_version,
        project_id=project_id,
        operator_id=current_user.id,
    )


@router.get("/forms", response_model=list[FormEntity])
async def list_my_forms(current_user: CurrentUser, form_service: FormServiceDep) -> list[FormEntity]:
    """Published forms in the operator's own project — deliberately bypasses
    the web permission system (FORMULARIO_READ), since seeing/filling out
    assigned forms is the operator's basic job, not an admin-granted privilege."""
    project_id = _require_project_id(current_user)
    return await form_service.search(None, FormStatus.PUBLISHED, str(project_id))


@router.get("/forms/{form_id}", response_model=FormEntity)
async def get_my_form(form_id: str, current_user: CurrentUser, form_service: FormServiceDep) -> FormEntity:
    project_id = _require_project_id(current_user)
    form = await form_service.get_form(form_id)
    if form.project_id != str(project_id):
        raise NotFoundError(f"Form {form_id} not found")
    return form


@router.post(
    "/attendances",
    response_model=AttendanceEntity,
    status_code=201,
    dependencies=[require_roles(Role.USER)],
)
async def submit_attendance(
    current_user: CurrentUser,
    form_service: FormServiceDep,
    attendance_service: AttendanceServiceDep,
    project_service: ProjectServiceDep,
    org_id: CurrentOrgId,
    storage: Annotated[StorageService, Depends(get_storage_service)],
    payload: Annotated[str, Form(...)],
    photo_files: list[UploadFile] = File(default=[]),
) -> AttendanceEntity:
    """Submits a completed form response from the field. Multipart: `payload`
    is the JSON body (see `AttendanceSubmitRequest`), `photo_files` are the
    raw image bytes, matched to `payload.photos` by list index — one entry
    per PHOTO/SIGNATURE field the operator answered."""
    project_id = _require_project_id(current_user)
    data = AttendanceSubmitRequest.model_validate_json(payload)

    form = await form_service.get_form(data.form_id)
    if form.project_id != str(project_id):
        raise NotFoundError(f"Form {data.form_id} not found")
    if form.status != FormStatus.PUBLISHED:
        raise BusinessRuleError("This form is not published")

    if len(data.photos) != len(photo_files):
        raise BusinessRuleError("photos metadata and uploaded files must have the same count")

    answered_field_ids = {response.field_id for response in data.responses}
    answered_field_ids.update(photo.field_id for photo in data.photos)
    missing = [field.label or field.id for field in form.fields if field.required and field.id not in answered_field_ids]
    if missing:
        raise BusinessRuleError(f"Missing required fields: {', '.join(missing)}")

    attendance_id = str(uuid.uuid4())
    signature_field_ids = {field.id for field in form.fields if field.type == FieldType.SIGNATURE}

    photos: list[AttendancePhoto] = []
    has_signature = False
    for meta, upload in zip(data.photos, photo_files):
        photo_id = str(uuid.uuid4())
        content = await upload.read()
        file_key = f"attendances/{attendance_id}/{photo_id}"
        await storage.upload_file(file_key, content, upload.content_type or "application/octet-stream")
        photos.append(AttendancePhoto(id=photo_id, field_id=meta.field_id, caption=meta.caption, file_key=file_key))
        if meta.field_id in signature_field_ids:
            has_signature = True

    project = await project_service.get_project(project_id, org_id)
    now = datetime.now(timezone.utc)

    attendance = AttendanceEntity(
        id="",
        form_id=data.form_id,
        form_name=form.name,
        operator_id=str(current_user.id),
        operator_name=current_user.name,
        project_id=str(project_id),
        project_name=project.name,
        duration=data.duration,
        responses=[
            AttendanceResponse(field_id=item.field_id, field_label=item.field_label, value=item.value)
            for item in data.responses
        ],
        photos=photos,
        signature=has_signature,
        gps_location=data.gps_location,
        created_at=now,
        completed_at=now,
        synced_at=now,
    )
    created = await attendance_service.create_attendance(attendance)
    await form_service.notify_attendance_submitted(data.form_id)
    return created
