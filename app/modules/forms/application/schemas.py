from pydantic import BaseModel, Field

from app.modules.forms.domain.entities import FieldType


class FormCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    project_id: str


class FormRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class CreateFieldRequest(BaseModel):
    type: FieldType
    order: int
