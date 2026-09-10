from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed validation or domain error point."""

    field: str | None = None
    issue: str
    type: str | None = None


class ErrorContainer(BaseModel):
    """Container holding error details."""

    code: str
    message: str
    request_id: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standardized top-level API error format."""

    error: ErrorContainer
