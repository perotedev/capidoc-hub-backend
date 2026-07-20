from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.shared.schema import CamelCaseModel


class FieldType(StrEnum):
    TEXT = "TEXT"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    CURRENCY = "CURRENCY"
    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"
    SELECT = "SELECT"
    MULTI_SELECT = "MULTI_SELECT"
    CHECKBOX = "CHECKBOX"
    RADIO = "RADIO"
    PHOTO = "PHOTO"
    SIGNATURE = "SIGNATURE"
    GPS = "GPS"


class FormStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class FormFieldOption(CamelCaseModel):
    id: str
    label: str
    value: str


class FormFieldValidation(CamelCaseModel):
    min_length: int | None = None
    max_length: int | None = None
    min: float | None = None
    max: float | None = None
    pattern: str | None = None
    max_photos: int | None = None
    require_gps: bool | None = None


class ConditionalLogic(CamelCaseModel):
    field_id: str
    operator: str
    value: str
    action: str


class FormField(CamelCaseModel):
    id: str
    type: FieldType
    label: str = ""
    description: str = ""
    required: bool = False
    order: int
    options: list[FormFieldOption] = Field(default_factory=list)
    validation: FormFieldValidation | None = None
    conditional_logic: ConditionalLogic | None = None
    chart_type: str | None = None


class FormSettings(CamelCaseModel):
    allow_photos: bool = True
    require_gps: bool = False
    require_signature: bool = False
    allow_offline: bool = True
    max_response_time: int | None = None


class TemplateConditionalRule(CamelCaseModel):
    id: str
    operator: str
    value: str
    text: str


class TemplateBoxBounds(CamelCaseModel):
    x: float
    y: float
    width: float
    height: float


class TemplateBoxAlignment(CamelCaseModel):
    horizontal: str = "left"
    vertical: str = "middle"


class TemplateBoxPadding(CamelCaseModel):
    top: float = 0
    right: float = 2
    bottom: float = 0
    left: float = 2


class TemplateBoxTextOptions(CamelCaseModel):
    word_wrap: bool = False
    overflow_behavior: str = "truncate"
    line_spacing: float = 1.2
    padding: TemplateBoxPadding = Field(default_factory=TemplateBoxPadding)
    uppercase: bool = False


class TemplateBoxStyle(CamelCaseModel):
    font_family: str = "Arial"
    font_size: int = 10
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str = "#000000"


class TemplateBox(CamelCaseModel):
    """Per-form PDF field layout.

    Schema mirrors the capidoc-tauri desktop app's `TextBox`/`DocumentProfile`
    model (bounds/alignment/text_options/style/conditional_rules) field-for-field
    so template JSON — and the PyMuPDF rendering logic that consumes it — is
    interchangeable between both apps ahead of their planned integration.
    """

    id: str
    field_id: str
    page_index: int = 0
    show_label: bool = False
    bounds: TemplateBoxBounds
    alignment: TemplateBoxAlignment = Field(default_factory=TemplateBoxAlignment)
    text_options: TemplateBoxTextOptions = Field(default_factory=TemplateBoxTextOptions)
    style: TemplateBoxStyle = Field(default_factory=TemplateBoxStyle)
    conditional_rules: list[TemplateConditionalRule] = Field(default_factory=list)


class FormEntity(CamelCaseModel):
    """Domain representation of a dynamic form, persisted as-is in MongoDB.

    Forms are inherently document-shaped (their `fields` are user-defined at
    runtime), so — unlike the Postgres-backed modules — this Pydantic model
    doubles as both the domain entity and the MongoDB document schema.
    """

    id: str
    name: str
    description: str = ""
    project_id: str
    status: FormStatus = FormStatus.DRAFT
    version: int = 1
    fields: list[FormField] = Field(default_factory=list)
    settings: FormSettings = Field(default_factory=FormSettings)
    template: list[TemplateBox] | None = None
    template_pdf_file_key: str | None = None
    created_by: str
    created_by_name: str
    attendances_count: int = 0
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
