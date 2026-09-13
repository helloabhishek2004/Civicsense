from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PriorityLevel, SeverityLevel


class PredictionConfidenceTier(str, Enum):
    """Explicit confidence governance tiers."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNCERTAIN = "UNCERTAIN"
    FAILED = "FAILED"


class CategoryPredictionItem(BaseModel):
    """Candidate category prediction with human-readable label and confidence score."""

    category: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(from_attributes=True)


class NormalizedPrediction(BaseModel):
    """Canonical normalized prediction schema decoupled from internal model representations."""

    predicted_category: str
    category_label: str
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_tier: PredictionConfidenceTier
    severity: SeverityLevel
    priority: PriorityLevel
    evidence_agreement: float | None = Field(None, ge=0.0, le=1.0)
    model_name: str
    model_version: str
    inference_source: str
    inference_time_ms: int = Field(ge=0)
    requires_review: bool
    review_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    top_predictions: list[CategoryPredictionItem] = Field(default_factory=list)
    decision_explanation: str
    hardware_acceleration: str = "NONE"
    timing_breakdown: dict[str, int | float | None] = Field(default_factory=dict)
    disclaimer: str = (
        "AI predictions are advisory suggestions and do not constitute official "
        "municipal verification."
    )

    model_config = ConfigDict(from_attributes=True)
