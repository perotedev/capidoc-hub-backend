from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseModel(BaseModel):
    """Base for API request/response schemas.

    Serializes/parses as camelCase over the wire (matching the Angular
    frontend's existing TypeScript interfaces) while the Python side keeps
    idiomatic snake_case field names. `populate_by_name` accepts both casings
    on input; FastAPI's default `response_model_by_alias=True` emits camelCase
    on output.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
