import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.common import ensure_utc


class DepartmentWorkloadStats(BaseModel):
    """Real-time operational workload metrics for a specific municipal department."""

    department_id: uuid.UUID
    department_name: str
    department_code: str
    total_assigned: int = Field(0, ge=0)
    pending_acknowledgment: int = Field(0, ge=0)
    in_progress: int = Field(0, ge=0)
    resolved: int = Field(0, ge=0)
    rejected_assignments: int = Field(0, ge=0)
    reassignment_required: int = Field(0, ge=0)

    model_config = ConfigDict(from_attributes=True)


class DepartmentRead(BaseModel):
    """Public representation of a municipal department."""

    id: uuid.UUID
    name: str
    code: str
    description: str | None = None
    head_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    sla_hours_default: int = 48
    is_active: bool = True
    created_at: datetime.datetime
    updated_at: datetime.datetime
    stats: DepartmentWorkloadStats | None = None

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


class DepartmentDetailRead(DepartmentRead):
    """Detailed department representation including complete operational statistics."""

    pass
