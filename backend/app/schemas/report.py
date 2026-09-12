import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.enums import PriorityLevel, ReportStatus
from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.assignment import AssignmentRead
from app.schemas.common import LocationSchema, ensure_utc
from app.schemas.evidence import EvidenceCreate, EvidenceRead
from app.schemas.verification import VerificationRead


class ClientProcessingSchema(BaseModel):
    """Client-side edge processing flags and versions."""

    enabled: bool = True
    processor_version: str = Field(..., max_length=32)
    image_preprocessed: bool = False
    text_preprocessed: bool = False
    embedding_generated: bool = False


class ImageQualitySchema(BaseModel):
    """Lightweight on-device image quality assessment and hash integrity."""

    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)
    aspect_ratio: float = Field(..., gt=0)
    file_size_bytes: int = Field(..., ge=0)
    mime_type: str = Field(..., max_length=64)
    sha256: str = Field(..., min_length=64, max_length=64)
    brightness: float | None = Field(None, ge=0.0, le=1.0)
    is_blurry: bool | None = None
    usable: bool = True
    feedback_message: str | None = Field(None, max_length=255)


class TextFeaturesSchema(BaseModel):
    """Normalized text features and transparent keyword hints."""

    raw_text: str | None = Field(None, max_length=5000)
    cleaned_text: str = Field(..., max_length=5000)
    character_count: int = Field(..., ge=0)
    word_count: int = Field(..., ge=0)
    language: str = Field("en", max_length=16)
    severity_terms: list[str] = Field(default_factory=list)
    urgency_terms: list[str] = Field(default_factory=list)
    category_terms: list[str] = Field(default_factory=list)
    location_terms: list[str] = Field(default_factory=list)
    safety_terms: list[str] = Field(default_factory=list)


class EdgeMetadataSchema(BaseModel):
    """Canonical edge-processing evidence contract package."""

    contract_version: str = Field("1.0.0", max_length=32)
    client_processing: ClientProcessingSchema
    image_quality: ImageQualitySchema | None = None
    text_features: TextFeaturesSchema | None = None
    category_hint: str | None = Field(None, max_length=64)
    embedding: list[float] | None = None  # None in Phase 1; reserved for future Phase 2


class ReportCreate(BaseModel):
    """Payload submitted by citizen or edge client to create a report."""

    location: LocationSchema
    description: str = Field(..., min_length=3, max_length=5000)
    category: str | None = Field(
        None, max_length=64, description="Citizen-selected civic issue category"
    )
    citizen_id: str | None = Field(None, max_length=128)
    citizen_name: str | None = Field(None, max_length=128)
    citizen_phone: str | None = Field(None, max_length=32)
    citizen_email: str | None = Field(None, max_length=255)
    citizen_postal_code: str | None = Field(None, max_length=32)
    evidence: list[EvidenceCreate] = Field(default_factory=list)
    client_report_id: uuid.UUID | None = Field(
        None, description="Optional client-generated UUID for offline sync idempotency"
    )
    edge_metadata: EdgeMetadataSchema | None = Field(
        None, description="Optional client edge-processing evidence and provenance metadata"
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
    category: str | None = None
    citizen_id: str | None = None
    citizen_name: str | None = None
    citizen_phone: str | None = None
    citizen_email: str | None = None
    citizen_postal_code: str | None = None
    latitude: float
    longitude: float
    address_hint: str | None = None
    description: str
    issue_id: uuid.UUID | None = None

    department_id: uuid.UUID | None = None
    department: str | None = None
    assigned_officer: str | None = None
    priority: PriorityLevel | None = None
    reassignment_required: bool = False

    evidences: list[EvidenceRead] = Field(default_factory=list)
    ai_analyses: list[AIAnalysisRead] = Field(default_factory=list)
    verifications: list[VerificationRead] = Field(default_factory=list)
    assignments: list[AssignmentRead] = Field(default_factory=list)
    current_assignment: AssignmentRead | None = None
    edge_metadata: dict[str, Any] | None = None

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


class ReportListResponse(BaseModel):
    """Paginated list response of reports."""

    items: list[ReportRead]
    total: int
    page: int
    page_size: int


class ReportStats(BaseModel):
    """Aggregated report intake, verification, and resolution metrics."""

    total_reports: int = Field(..., alias="totalReports", ge=0)
    pending_review: int = Field(..., alias="pendingReview", ge=0)
    in_progress: int = Field(..., alias="inProgress", ge=0)
    resolved_today: int = Field(..., alias="resolvedToday", ge=0)
    critical_issues: int = Field(..., alias="criticalIssues", ge=0)
    avg_resolution_days: float = Field(0.0, alias="avgResolutionDays", ge=0.0)
    human_override_rate: float = Field(0.0, alias="humanOverrideRate", ge=0.0)
    ai_agreement_rate: float = Field(100.0, alias="aiAgreementRate", ge=0.0)

    model_config = ConfigDict(populate_by_name=True)
