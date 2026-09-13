import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.ai.normalized_prediction import PredictionNormalizer


class BenchmarkSplit(str, Enum):
    """Standard benchmark partition splits."""

    TRAIN = "train"
    VAL = "val"
    TEST = "test"
    BENCHMARK = "benchmark"


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates with label."""

    label: str = Field(..., min_length=1)
    x_min: float = Field(..., ge=0.0, le=1.0)
    y_min: float = Field(..., ge=0.0, le=1.0)
    x_max: float = Field(..., ge=0.0, le=1.0)
    y_max: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_coordinates(self) -> "BoundingBox":
        if self.x_max < self.x_min:
            msg = f"Invalid x coordinates: x_max ({self.x_max}) is less than x_min ({self.x_min})"
            raise ValueError(msg)
        if self.y_max < self.y_min:
            msg = f"Invalid y coordinates: y_max ({self.y_max}) is less than y_min ({self.y_min})"
            raise ValueError(msg)
        return self

    model_config = ConfigDict(from_attributes=True)


class EvaluationSample(BaseModel):
    """Canonical dataset-independent evaluation sample record."""

    sample_id: str = Field(..., min_length=1, description="Unique identifier for evaluation sample")
    image_rel_path: str | None = Field(
        None, description="Relative path to image file from benchmark root"
    )
    source_dataset: str = Field(
        ..., min_length=1, description="Name of source dataset (such as RDD2022, TACO)"
    )
    source_record_id: str = Field(..., min_length=1, description="Identifier in upstream dataset")
    canonical_category: str = Field(..., description="Normalized CivicSense canonical category")
    original_category: str = Field(..., description="Original label from source dataset")
    category_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    bounding_boxes: list[BoundingBox] = Field(default_factory=list)
    text_description: str | None = Field(None, max_length=5000)
    split: BenchmarkSplit = BenchmarkSplit.BENCHMARK
    license: str = Field(..., min_length=1)
    license_url: str = Field(..., min_length=1)
    attribution: str = Field(..., min_length=1)
    is_blurry: bool = False
    is_low_res: bool = False
    sha256: str = Field(..., min_length=64, max_length=64)
    phash: str = Field(..., min_length=1)
    duplicate_group_id: str | None = None
    review_status: str = Field("CONFIRMED", max_length=32)
    verification_level: str = Field(
        default="source_verified",
        description=(
            "Ground truth quality: source_verified, manually_verified, "
            "weak_source_label, ambiguous"
        ),
    )
    visual_relevance: str = Field(
        default="direct_issue_visible",
        description="Visual relevance level: direct_issue_visible, indirect_evidence, unclear",
    )
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("canonical_category")
    @classmethod
    def validate_canonical_category(cls, value: str) -> str:
        if value not in PredictionNormalizer.CATEGORY_LABELS:
            allowed = list(PredictionNormalizer.CATEGORY_LABELS.keys())
            msg = f"Category '{value}' is not in authoritative taxonomy: {allowed}"
            raise ValueError(msg)
        return value

    @field_validator("verification_level")
    @classmethod
    def validate_verification_level(cls, value: str) -> str:
        valid_tiers = {"source_verified", "manually_verified", "weak_source_label", "ambiguous"}
        if value not in valid_tiers:
            msg = f"verification_level '{value}' must be one of {sorted(valid_tiers)}"
            raise ValueError(msg)
        return value

    @field_validator("visual_relevance")
    @classmethod
    def validate_visual_relevance(cls, value: str) -> str:
        valid_tiers = {"direct_issue_visible", "indirect_evidence", "unclear"}
        if value not in valid_tiers:
            msg = f"visual_relevance '{value}' must be one of {sorted(valid_tiers)}"
            raise ValueError(msg)
        return value

    model_config = ConfigDict(from_attributes=True)


class BenchmarkManifest(BaseModel):
    """Metadata manifest summarizing an assembled benchmark distribution."""

    benchmark_version: str = Field(..., min_length=1)
    generation_timestamp: datetime.datetime | str
    total_sample_count: int = Field(..., ge=0)
    category_counts: dict[str, int] = Field(default_factory=dict)
    source_dataset_counts: dict[str, int] = Field(default_factory=dict)
    verification_level_counts: dict[str, int] = Field(default_factory=dict)
    visual_relevance_counts: dict[str, int] = Field(default_factory=dict)
    image_root: str = "images"
    schema_version: str = "1.0.0"
    generator_version: str = "1.0.0"
    integrity_hash: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EvaluationResultRecord(BaseModel):
    """Outcome of evaluating a single sample through an inference pipeline."""

    sample_id: str
    ground_truth_category: str
    predicted_category: str
    confidence: float
    confidence_tier: str
    review_required: bool
    review_reasons: list[str] = Field(default_factory=list)
    latency_ms: float = Field(ge=0.0)
    is_correct: bool
    evaluation_mode: str
    predicted_severity: str | None = None
    ground_truth_severity: str | None = None
    failure_type: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    pipeline_errors: list[str] = Field(default_factory=list)
    timing_breakdown: dict[str, int | float | None] = Field(default_factory=dict)
    decision_explanation: str | None = None
    evidence_agreement: float | None = None

    model_config = ConfigDict(from_attributes=True)
