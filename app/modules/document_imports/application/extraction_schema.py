"""Builds the "extraction template" sent to n8n: a JSON Schema an AI
structured-output node can bind to directly, plus a ready-to-use natural
language prompt — both derived from the form's own (dynamic) field
definitions, so nothing about the target fields is hardcoded per-form."""

from app.modules.forms.domain.entities import FieldType, FormField

NON_EXTRACTABLE_FIELD_TYPES = {FieldType.PHOTO, FieldType.SIGNATURE, FieldType.GPS}


def extractable_fields(fields: list[FormField]) -> list[FormField]:
    return [field for field in fields if field.type not in NON_EXTRACTABLE_FIELD_TYPES]


def build_form_fields_payload(fields: list[FormField]) -> list[dict]:
    return [
        {
            "id": field.id,
            "label": field.label,
            "type": field.type.value,
            "description": field.description,
            "required": field.required,
            "options": [{"value": option.value, "label": option.label} for option in field.options],
        }
        for field in extractable_fields(fields)
    ]


def _field_json_schema(field: FormField) -> dict:
    """One field's JSON Schema property — every value is a string (matching
    the confirm/attendance contract, which stores every response as text),
    but `enum` constrains SELECT/RADIO/CHECKBOX to their valid values so an
    AI node can't return something the form wouldn't accept."""
    schema: dict = {"type": "string", "description": field.label or field.id}
    if field.description:
        schema["description"] += f" — {field.description}"

    if field.type in (FieldType.SELECT, FieldType.RADIO) and field.options:
        schema["enum"] = [option.value for option in field.options]
    elif field.type == FieldType.MULTI_SELECT and field.options:
        allowed = ", ".join(option.value for option in field.options)
        schema["description"] += f" (múltiplos valores separados por vírgula, dentre: {allowed})"
    elif field.type == FieldType.CHECKBOX:
        schema["enum"] = ["true", "false"]

    return schema


def build_extraction_json_schema(fields: list[FormField]) -> dict:
    """A JSON Schema with one named property per field (keyed by field id) —
    drop this straight into an n8n AI node's "Structured Output" / OpenAI
    `response_format: json_schema` config to force the model's answer into
    exactly the shape `POST .../callback` expects as `values`."""
    targets = extractable_fields(fields)
    properties = {field.id: _field_json_schema(field) for field in targets}
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


def build_extraction_prompt(form_name: str, fields: list[FormField]) -> str:
    """A ready-to-paste instruction for a plain LLM prompt node (as an
    alternative to a strict JSON-schema node) — describes each field in
    natural language and pins down the expected JSON output shape."""
    lines = [
        f'Extraia do documento anexado os valores para os campos do formulário "{form_name}".',
        'Responda estritamente em JSON, no formato {"<fieldId>": "<valor extraído como texto>", ...}, '
        "usando exatamente os IDs de campo abaixo como chaves.",
        "Se um campo não for encontrado no documento, omita a chave (não invente valores).",
        "",
        "Campos a extrair:",
    ]
    for field in extractable_fields(fields):
        parts = [f'- "{field.id}" ({field.label}, tipo {field.type.value})']
        if field.description:
            parts.append(f"— {field.description}")
        if field.options:
            allowed = ", ".join(f'"{option.value}"' for option in field.options)
            parts.append(f"— valores permitidos: [{allowed}]")
        lines.append(" ".join(parts))
    return "\n".join(lines)
