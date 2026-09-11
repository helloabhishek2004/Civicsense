import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PriorityLevel, ReportStatus
from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.common import LocationSchema
from app.schemas.evidence import EvidenceCreate, EvidenceRead
from app.schemas.verification import VerificationRead


class ReportCreate(BaseModel):
    """Payload submitted by citizen or edge client to create a report."""

    location: LocationSchema
    description: str = Field(..., min_length=3, max_length=5000)
    citizen_id: str | None = Field(None, max_length=128)
    evidence: list[EvidenceCreate] = Field(default_factory=list)
    client_report_id: uuid.UUID | None = Field(
        None, description="Optional client-generated UUID for offline sync idempotency"
    )


class ReportTransitionRequest(BaseModel):
    """Payload to advance or change report lifecycle status."""

    next_status: ReportStatus
    department: str | None = Field(None, max_length=64)
    assigned_officer: str | None = Field(None, max_length=128)
    priority: PriorityLevel | None = None
    reason: str | None = Field(None, max_length=1000)
    notes: str | None = Field(None, max_length=2000)
    actor: str | None = Field(None, max_length=128)


class ReportRead(BaseModel):
    """Full representation of a citizen report."""

    id: uuid.UUID
    tracking_id: str
    status: ReportStatus
    citizen_id: str | None = None
    latitude: float
    longitude: float
    address_hint: str | None = None
    description: str
    issue_id: uuid.UUID | None = None

    department: str | None = None
    assigned_officer: str | None = None
    priority: PriorityLevel | None = None

    evidences: list[EvidenceRead] = Field(default_factory=list)
    ai_analyses: list[AIAnalysisRead] = Field(default_factory=list)
    verifications: list[VerificationRead] = Field(default_factory=list)

    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    """Paginated list response of reports."""

    items: list[ReportRead]
    total: int
    page: int
    page_size: int
