import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SeverityLevel, VerificationDecision


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

    model_config = ConfigDict(from_attributes=True)
