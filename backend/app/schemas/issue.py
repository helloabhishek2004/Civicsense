import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.common import ensure_utc


class IssueRead(BaseModel):
    """Schema for underlying civic issues grouping one or more reports."""

    id: uuid.UUID
    title: str
    category: str
    status: str
    primary_latitude: float = Field(..., ge=-90.0, le=90.0)
    primary_longitude: float = Field(..., ge=-180.0, le=180.0)
    report_count: int = Field(0, ge=0)

    # Priority ranking fields
    priority_score: float | None = None
    priority_level: str | None = None
    priority_computed_at: datetime.datetime | None = None

    created_at: datetime.datetime
    updated_at: datetime.datetime

    @field_validator("created_at", "updated_at", "priority_computed_at", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        return ensure_utc(v)

    @field_serializer(
        "created_at", "updated_at", "priority_computed_at",
        when_used="json-unless-none",
    )
    def serialize_utc(self, v: datetime.datetime | None) -> str | None:
        if v is None:
            return None
        res = ensure_utc(v)
        assert res is not None
        return res.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)


class IssueListResponse(BaseModel):
    """Paginated list of issues."""

    items: list[IssueRead]
    total: int
    page: int
    page_size: int


class PriorityBreakdownRead(BaseModel):
    """Full priority breakdown for a single issue."""

    issue_id: uuid.UUID
    priority_score: float | None = None
    priority_level: str | None = None
    priority_computed_at: datetime.datetime | None = None
    breakdown: dict[str, Any] | None = None

    @field_validator("priority_computed_at", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        return ensure_utc(v)

    @field_serializer("priority_computed_at", when_used="json-unless-none")
    def serialize_utc(self, v: datetime.datetime | None) -> str | None:
        if v is None:
            return None
        res = ensure_utc(v)
        assert res is not None
        return res.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)


class IssueUpdate(BaseModel):
    """Payload for updating an issue status or title."""

    title: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=64)
    status: str | None = Field(None, max_length=32)
