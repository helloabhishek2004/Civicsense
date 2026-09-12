import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.enums import SeverityLevel, VerificationDecision
from app.schemas.common import ensure_utc


class VerificationCreate(BaseModel):
    """Payload for submitting a human review verdict."""

    decision: VerificationDecision
    reviewer_id: str | None = Field(None, max_length=128)
    verified_category: str | None = Field(None, max_length=64)
    verified_severity: SeverityLevel | None = None
    notes: str | None = None


class VerificationRead(VerificationCreate):
    """Schema for returning human verification records."""

    id: uuid.UUID
    report_id: uuid.UUID
    created_at: datetime.datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime.datetime) -> datetime.datetime:
        res = ensure_utc(v)
        assert res is not None
        return res

    @field_serializer("created_at", when_used="json-unless-none")
    def serialize_utc(self, v: datetime.datetime) -> str:
        res = ensure_utc(v)
        assert res is not None
        return res.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)
