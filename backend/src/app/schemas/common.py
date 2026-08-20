from pydantic import BaseModel, ConfigDict


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class Error(BaseModel):
    """The single error envelope for every failure (FR-056)."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


class FieldError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    message: str


class ValidationErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = "validation_failed"
    message: str
    fields: list[FieldError]


class ValidationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ValidationErrorBody


class Page[T](BaseModel):
    """Generic paged-list wrapper matching UserPage/AuditPage in
    contracts/openapi.yaml."""

    model_config = ConfigDict(extra="forbid")

    items: list[T]
    page: int
    page_size: int
    total: int
