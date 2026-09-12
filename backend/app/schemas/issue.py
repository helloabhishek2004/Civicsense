import datetime
import uuid

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
    report_count: int = Field(1, ge=1)
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime.datetime) -> datetime.datetime:
        res = ensure_utc(v)
        assert res is not None
        return res

    @field_serializer("created_at", "updated_at", when_used="json-unless-none")
    def serialize_utc(self, v: datetime.datetime) -> str:
        res = ensure_utc(v)
        assert res is not None
        return res.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)


class IssueUpdate(BaseModel):
    """Payload for updating an issue status or title."""

    title: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=64)
    status: str | None = Field(None, max_length=32)
