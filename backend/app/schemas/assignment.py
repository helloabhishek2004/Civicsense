import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.enums import AssignmentStatus, DepartmentRejectionReason
from app.schemas.common import ensure_utc


class AssignmentRead(BaseModel):
    """Schema for reading a report assignment audit record."""

    id: uuid.UUID
    report_id: uuid.UUID
    department_id: uuid.UUID | None = None
    department_name: str
    assigned_by: str
    assigned_to_officer: str | None = None
    status: AssignmentStatus
    rejection_reason: DepartmentRejectionReason | None = None
    notes: str | None = None
    created_at: datetime.datetime
    resolved_at: datetime.datetime | None = None

    @field_validator("created_at", "resolved_at", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        return ensure_utc(v)

    @field_serializer("created_at", "resolved_at", when_used="json-unless-none")
    def serialize_utc(self, v: datetime.datetime | None) -> str | None:
        if v is None:
            return None
        res = ensure_utc(v)
        assert res is not None
        return res.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)


class DepartmentAssignRequest(BaseModel):
    """Payload to assign a report to a municipal department."""

    department_id: uuid.UUID | None = None
    department_name: str | None = Field(None, max_length=64)
    assigned_by: str = Field("Triage Officer", max_length=128)
    assigned_to_officer: str | None = Field(None, max_length=128)
    notes: str | None = Field(None, max_length=2000)


class DepartmentAcknowledgeRequest(BaseModel):
    """Payload when department acknowledges and accepts an assigned job."""

    assigned_to_officer: str | None = Field(None, max_length=128)
    notes: str | None = Field(None, max_length=2000)


class DepartmentCompleteRequest(BaseModel):
    """Payload when department marks work completed."""

    resolver_notes: str = Field(..., min_length=5, max_length=2000)
    resolved_by: str | None = Field(None, max_length=128)


class DepartmentRejectRequest(BaseModel):
    """Payload when department declines an assignment and returns it to triage."""

    rejection_reason: DepartmentRejectionReason
    notes: str = Field(..., min_length=5, max_length=2000)
    suggested_department: str | None = Field(None, max_length=64)
