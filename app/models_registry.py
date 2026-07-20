"""Imports every SQLAlchemy model so they register with `Base.metadata`.

Alembic's autogenerate needs all models imported at least once before it
diffs the metadata against the live database — this module is that single
import point, referenced from `alembic/env.py`.
"""

from app.modules.departments.infrastructure.models import DepartmentModel  # noqa: F401
from app.modules.devices.infrastructure.models import (  # noqa: F401
    DeviceDownloadDetailModel,
    DeviceDownloadModel,
    DeviceModel,
)
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
from app.modules.organizations.infrastructure.models import OrganizationModel  # noqa: F401
from app.modules.projects.infrastructure.models import ProjectModel  # noqa: F401
from app.modules.reports.infrastructure.models import (  # noqa: F401
    ReportFilterDepartmentModel,
    ReportFilterFormModel,
    ReportFilterOperatorModel,
    ReportModel,
)
from app.modules.users.infrastructure.models import UserModel  # noqa: F401
