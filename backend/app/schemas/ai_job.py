import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AIJobStatus, AIProcessingStage
from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.verification import VerificationRead


class AIJobEventRead(BaseModel):
    """Schema for returning granular stage audit events."""

    id: uuid.UUID
    job_id: uuid.UUID
    report_id: uuid.UUID
    stage: AIProcessingStage
    status: str
    message: str
    metadata_json: dict[str, Any] | None = None
    started_at: datetime.datetime
    completed_at: datetime.datetime | None = None
    duration_ms: int | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class AIJobRead(BaseModel):
    """Full representation of an AI processing job."""

    id: uuid.UUID
    report_id: uuid.UUID
    status: AIJobStatus
    current_stage: AIProcessingStage
    review_required: bool
    review_completed: bool
    review_reason: str | None = None
    queued_at: datetime.datetime
    started_at: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None
    failed_at: datetime.datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    attempt_count: int
    execution_mode: str
    processor_name: str
    worker_id: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    events: list[AIJobEventRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AIJobListResponse(BaseModel):
    """Paginated response of AI processing jobs."""

    items: list[AIJobRead]
    total: int
    page: int
    page_size: int


class ReportAIResult(BaseModel):
    """Composite schema combining AI job status, analysis results, and provenance."""

    report_id: uuid.UUID
    tracking_id: str
    report_status: str
    latest_job: AIJobRead | None = None
    ai_analysis: AIAnalysisRead | None = None
    verification: VerificationRead | None = None
    execution_mode: str
    processor_name: str
    disclaimer: str = (
        "Deterministic Prototype AI / Demo Simulation. "
        "Rule-based text pattern & vision metadata analysis. Not a trained deep learning model."
    )


class AIHealthResponse(BaseModel):
    """Truthful health check and capability disclosure for the AI system."""

    status: str
    execution_mode: str
    processor_mode: str
    processor_name: str
    production_model_available: bool
    background_worker_available: bool
    supported_stages: list[str]
    active_jobs_count: int
    total_jobs_processed: int
    last_processed_at: datetime.datetime | None = None
    timestamp: datetime.datetime
