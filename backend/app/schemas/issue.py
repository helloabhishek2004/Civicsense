import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class IssueRead(BaseModel):
    """Schema for underlying civic issues grouping one or more reports."""

    id: uuid.UUID
    title: str
    category: str
    status: str
    primary_latitude: float = Field(..., ge=-90.0, le=90.0)
    primary_longitude: float = Field(..., ge=-180.0, le=180.0)
    report_count: int = Field(1, ge=1)
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class IssueUpdate(BaseModel):
    """Payload for updating an issue status or title."""

    title: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=64)
    status: str | None = Field(None, max_length=32)
