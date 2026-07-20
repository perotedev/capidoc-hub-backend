from enum import StrEnum


class Role(StrEnum):
    """User roles, mirrored from the Angular frontend's `Role` enum.

    SUPER_ADMIN: the platform operator. Creates ADMIN (and AUDITOR) accounts
    but has no access to any organization's tenant data — only cross-org
    metadata (counts), never content.
    ADMIN: owns one organization (a tenant). Full, unrestricted access within
    it; creates its AUDITOR/USER accounts and its projects.
    AUDITOR: read-only across everything in its organization — no create,
    update, or delete under any circumstance, regardless of permission grants.
    USER: access within its organization is governed entirely by the
    Permissions module (groups + individual resource grants).
    """

    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"
    USER = "USER"


class Resource(StrEnum):
    """Permission resources, mirrored from the Angular frontend's `RESOURCE_OPERATIONS` map."""

    PROJETO = "PROJETO"
    USUARIO = "USUARIO"
    DEPARTAMENTO = "DEPARTAMENTO"
    FORMULARIO = "FORMULARIO"
    ATENDIMENTO = "ATENDIMENTO"
    DOCUMENTO = "DOCUMENTO"
    OPERADOR = "OPERADOR"
    DASHBOARD = "DASHBOARD"
    PERMISSAO = "PERMISSAO"
    DISPOSITIVO = "DISPOSITIVO"
    RELATORIO = "RELATORIO"


class PermissionOperation(StrEnum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
