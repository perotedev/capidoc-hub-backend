from pydantic import Field

from app.modules.forms.domain.entities import FieldType
from app.shared.schema import CamelCaseModel


class FormCreateRequest(CamelCaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    project_id: str


class FormRenameRequest(CamelCaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class CreateFieldRequest(CamelCaseModel):
    type: FieldType
    order: int
