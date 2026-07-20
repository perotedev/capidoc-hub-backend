from fastapi import APIRouter

from app.modules.attendances.api.v1.endpoints import router as attendances_router
from app.modules.auth.api.v1.endpoints import router as auth_router
from app.modules.dashboards_custom.api.v1.endpoints import router as dashboards_custom_router
from app.modules.departments.api.v1.endpoints import router as departments_router
from app.modules.devices.api.v1.endpoints import router as devices_router
from app.modules.document_imports.api.v1.endpoints import router as document_imports_router
from app.modules.documents.api.v1.endpoints import router as documents_router
from app.modules.documents.api.v1.endpoints import templates_router as document_templates_router
from app.modules.forms.api.v1.endpoints import router as forms_router
from app.modules.mobile.api.v1.endpoints import router as mobile_router
from app.modules.mobile.api.v1.websocket import router as mobile_websocket_router
from app.modules.notifications.api.v1.endpoints import router as notifications_router
from app.modules.operators.api.v1.endpoints import router as operators_router
from app.modules.organizations.api.v1.endpoints import router as organizations_router
from app.modules.permissions.api.v1.endpoints import router as permissions_router
from app.modules.projects.api.v1.endpoints import router as projects_router
from app.modules.reports.api.v1.endpoints import router as reports_router
from app.modules.users.api.v1.endpoints import router as users_router
from app.modules.validation.api.v1.endpoints import router as validation_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(departments_router)
api_v1_router.include_router(permissions_router)
api_v1_router.include_router(forms_router)
api_v1_router.include_router(attendances_router)
api_v1_router.include_router(operators_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(document_templates_router)
api_v1_router.include_router(devices_router)
api_v1_router.include_router(document_imports_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(dashboards_custom_router)
api_v1_router.include_router(validation_router)
api_v1_router.include_router(mobile_router)
api_v1_router.include_router(mobile_websocket_router)
api_v1_router.include_router(notifications_router)
