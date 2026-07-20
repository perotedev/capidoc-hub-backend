"""Imports every SQLAlchemy model so they register with `Base.metadata`.

Alembic's autogenerate needs all models imported at least once before it
diffs the metadata against the live database — this module is that single
import point, referenced from `alembic/env.py`.
"""

from app.modules.activities.infrastructure.models import ActivityModel  # noqa: F401
from app.modules.departments.infrastructure.models import DepartmentModel  # noqa: F401
from app.modules.devices.infrastructure.models import (  # noqa: F401
    DeviceDownloadDetailModel,
    DeviceDownloadModel,
    DeviceModel,
)
from app.modules.document_imports.infrastructure.models import DocumentImportModel  # noqa: F401
from app.modules.documents.infrastructure.models import (  # noqa: F401
    DocumentModel,
    DocumentTemplateModel,
)
from app.modules.dashboards_custom.infrastructure.models import (  # noqa: F401
    DashboardCustomModel,
    DashboardShareModel,
    DashboardWidgetModel,
)
from app.modules.permissions.infrastructure.models import (  # noqa: F401
    GroupPermissionModel,
    PermissionGroupMemberModel,
    PermissionGroupModel,
    UserPermissionModel,
)
from app.modules.notifications.infrastructure.models import NotificationModel  # noqa: F401
from app.modules.organizations.infrastructure.models import OrganizationModel  # noqa: F401
from app.modules.projects.infrastructure.models import ProjectModel  # noqa: F401
from app.modules.reports.infrastructure.models import (  # noqa: F401
    ReportFilterDepartmentModel,
    ReportFilterFormModel,
    ReportFilterOperatorModel,
    ReportModel,
)
from app.modules.users.infrastructure.models import UserModel  # noqa: F401
from app.modules.whatsapp_auth.infrastructure.models import WhatsAppAuthorizationModel  # noqa: F401
from app.modules.whatsapp_bot.infrastructure.models import WhatsAppConversationModel  # noqa: F401
