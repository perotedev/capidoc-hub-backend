from enum import StrEnum


class Role(StrEnum):
    """User roles, mirrored from the Angular frontend's `Role` enum."""

    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN_PROJECT = "ADMIN_PROJECT"
    GESTOR = "GESTOR"
    OPERADOR = "OPERADOR"
    AUDITOR = "AUDITOR"


class Resource(StrEnum):
    """Permission resources, mirrored from the Angular frontend's `RESOURCE_OPERATIONS` map."""

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
