"""CivicSense Versioned Training Dataset Schema and Data Models.

Defines Pydantic v2 data models, enums, and validators for:
- Individual training sample records (TrainingSample)
- Leakage check verification structures (BenchmarkLeakageCheckResult)
- Dataset summary metadata (TrainingDatasetSummary)

Adheres strictly to the CivicSense Annotation Taxonomy (v1.0).
"""

from __future__ import annotations

import datetime
import re
from enum import Enum
from pathlib import PurePath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.ai.normalized_prediction import PredictionNormalizer

CANONICAL_CATEGORIES = set(PredictionNormalizer.CATEGORY_LABELS.keys())
HEX_64_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
HEX_16_PATTERN = re.compile(r"^[0-9a-fA-F]{16}$")

VALID_OTHER_SUBTYPES: set[str] = {
    "missing_road_sign",
    "damaged_road_sign",
    "damaged_guardrail",
    "fallen_tree_blockage",
    "graffiti",
    "broken_bench",
    "damaged_sidewalk",
    "other_documented_civic_defect",
}


class TrainingSplit(str, Enum):
    """Partitions for training dataset samples."""

    TRAIN = "train"
    VALIDATION = "validation"
    QUARANTINE = "quarantine"


class AmbiguityStatus(str, Enum):
    """Visual ambiguity and domain suitability statuses."""

    CLEAR = "clear"
    AMBIGUOUS = "ambiguous"
    QUARANTINE = "quarantine"
    UNUSABLE = "unusable"
    OUT_OF_DOMAIN = "out_of_domain"
    NO_VISIBLE_ISSUE = "no_visible_issue"


class VerificationMethod(str, Enum):
    """Method used to establish ground truth."""

    SOURCE_LABEL = "source_label"
    MANUAL_REVIEW = "manual_review"
    CROSS_VERIFIED = "cross_verified"


class LicenseScope(str, Enum):
    """Level at which license is established."""

    IMAGE = "image"
    RECORD = "record"
    DATASET = "dataset"


class TrainingQualityFlag(str, Enum):
    """Visual quality flags."""

    IS_BLURRY = "is_blurry"
    IS_LOW_RES = "is_low_res"
    LIGHTING_POOR = "lighting_poor"
    EXTREME_ASPECT_RATIO = "extreme_aspect_ratio"
    HEAVY_OCCLUSION = "heavy_occlusion"


class LeakageStatus(str, Enum):
    """Outcome of checking a candidate sample against the frozen evaluation benchmark."""

    PASSED = "passed"
    FAILED_EXACT_SHA256 = "failed_exact_sha256"
    FAILED_SOURCE_ID = "failed_source_id"
    FAILED_SOURCE_URL = "failed_source_url"
    FAILED_DHASH_NEAR_DUPLICATE = "failed_dhash_near_duplicate"
    NOT_CHECKED = "not_checked"


class BenchmarkLeakageCheckResult(BaseModel):
    """Audit outcome for benchmark leakage check."""

    status: LeakageStatus = LeakageStatus.NOT_CHECKED
    checked: bool = False
    passed: bool = False
    min_dhash_distance: int | None = Field(
        default=None, ge=0, le=64, description="Minimum Hamming distance to any benchmark sample"
    )
    matched_benchmark_sample_id: str | None = Field(
        default=None, description="Benchmark sample ID if collision occurred"
    )
    details: str | None = Field(default=None, description="Human-readable audit note")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.lower()
        return value

    model_config = ConfigDict(from_attributes=True)



class TrainingSample(BaseModel):
    """Canonical dataset record for the CivicSense training pool."""

    sample_id: str = Field(..., min_length=1, description="Unique training sample identifier")
    dataset_version: str = Field("training_v1", min_length=1)
    source_name: str = Field(..., min_length=1, description="Upstream source dataset identifier")
    source_record_id: str = Field(..., min_length=1, description="Original record ID in source")
    source_url: str = Field(..., min_length=1, description="Source webpage or direct asset URL")
    license: str = Field(..., min_length=1, description="Legal license identifier")
    license_url: str | None = Field(
        None, description="URL to legal license text when available"
    )
    license_scope: LicenseScope = Field(
        LicenseScope.DATASET, description="Level at which license is documented"
    )
    local_path: str = Field(..., min_length=1, description="Relative path from dataset root")
    sha256: str = Field(..., min_length=64, max_length=64, description="Cryptographic SHA-256")
    phash: str | None = Field(None, description="Perceptual pHash hex string if available")
    dhash: str = Field(..., min_length=16, max_length=16, description="64-bit dHash hex string")
    width: int = Field(..., gt=0, description="Image width in pixels")
    height: int = Field(..., gt=0, description="Image height in pixels")
    file_size_bytes: int = Field(..., gt=0, description="File size in bytes")
    mime_type: str = Field(..., min_length=1, description="Image MIME type (e.g. image/jpeg)")
    primary_category: str = Field(..., description="Canonical CivicSense category")
    secondary_categories: list[str] = Field(
        default_factory=list, description="Secondary or co-occurring category labels"
    )
    has_multiple_issues: bool = Field(
        default=False, description="Whether multiple civic issues were observed"
    )
    quality_flags: list[str] = Field(
        default_factory=list, description="Quality warnings or flags"
    )
    ambiguity_status: AmbiguityStatus = Field(
        AmbiguityStatus.CLEAR, description="Ambiguity and domain status"
    )
    verification_status: str = Field(
        "UNVERIFIED", description="Verification state: UNVERIFIED, VERIFIED_CLEAN, QUARANTINED"
    )
    verification_method: VerificationMethod = Field(
        VerificationMethod.SOURCE_LABEL, description="Verification provenance"
    )
    reviewer_notes: str | None = Field(None, max_length=5000)
    subtype: str | None = Field(
        default=None, description="Detailed visual defect subtype, required for 'Other'"
    )
    group_id: str = Field(..., min_length=1, description="Incident or burst capture group ID")
    split: TrainingSplit = Field(TrainingSplit.TRAIN, description="Assigned dataset split")
    benchmark_leakage_check: BenchmarkLeakageCheckResult = Field(
        default_factory=lambda: BenchmarkLeakageCheckResult()
    )
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat()
    )
    schema_version: str = Field("1.0.0", min_length=1)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("primary_category")
    @classmethod
    def validate_primary_category(cls, value: str) -> str:
        if value not in CANONICAL_CATEGORIES:
            allowed = sorted(CANONICAL_CATEGORIES)
            msg = f"primary_category '{value}' is not in canonical taxonomy: {allowed}"
            raise ValueError(msg)
        return value


    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not HEX_64_PATTERN.match(value):
            msg = f"sha256 must be exactly 64 hexadecimal characters, got '{value}'"
            raise ValueError(msg)
        return value.lower()

    @field_validator("dhash")
    @classmethod
    def validate_dhash(cls, value: str) -> str:
        if not HEX_16_PATTERN.match(value):
            msg = f"dhash must be exactly 16 hexadecimal characters, got '{value}'"
            raise ValueError(msg)
        return value.lower()

    @field_validator("local_path")
    @classmethod
    def validate_local_path(cls, value: str) -> str:
        pure = PurePath(value)
        if pure.is_absolute():
            msg = f"local_path must be relative to dataset root, got absolute path '{value}'"
            raise ValueError(msg)
        if ".." in pure.parts:
            msg = f"local_path contains illegal path traversal '..': '{value}'"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_invariants(self) -> TrainingSample:
        # 1. Primary category must not be duplicated in secondary_categories
        if self.primary_category in self.secondary_categories:
            self.secondary_categories = [
                c for c in self.secondary_categories if c != self.primary_category
            ]

        # 2. If secondary categories exist, has_multiple_issues must be True
        if self.secondary_categories and not self.has_multiple_issues:
            self.has_multiple_issues = True

        # 3. Quarantine Isolation Rule:
        # If ambiguity is not CLEAR, or verification_status is QUARANTINED,
        # the split MUST be QUARANTINE to guarantee it cannot enter train or validation.
        non_clear_ambiguities = {
            AmbiguityStatus.AMBIGUOUS,
            AmbiguityStatus.QUARANTINE,
            AmbiguityStatus.UNUSABLE,
            AmbiguityStatus.OUT_OF_DOMAIN,
            AmbiguityStatus.NO_VISIBLE_ISSUE,
        }
        if (
            self.ambiguity_status in non_clear_ambiguities
            or self.verification_status.upper() == "QUARANTINED"
        ):
            if self.split != TrainingSplit.QUARANTINE:
                msg = (
                    f"Sample {self.sample_id} with ambiguity '{self.ambiguity_status.value}' "
                    f"or verification '{self.verification_status}' must have split=QUARANTINE, "
                    f"got split='{self.split.value}'"
                )
                raise ValueError(msg)

        # 4. Leakage rejection must also force quarantine
        if self.benchmark_leakage_check.checked and not self.benchmark_leakage_check.passed:
            if self.split != TrainingSplit.QUARANTINE:
                msg = (
                    f"Sample {self.sample_id} failed benchmark leakage check "
                    f"({self.benchmark_leakage_check.status.value}) and must be QUARANTINE"
                )
                raise ValueError(msg)

        # 5. Other subtype validation
        if self.primary_category == "Other" and self.subtype is not None:
            if self.subtype not in VALID_OTHER_SUBTYPES:
                allowed = sorted(VALID_OTHER_SUBTYPES)
                msg = (
                    f"Sample {self.sample_id} has invalid Other subtype '{self.subtype}'. "
                    f"Must be one of {allowed}"
                )
                raise ValueError(msg)

        return self


class TrainingDatasetSummary(BaseModel):
    """Aggregate dataset summary and distribution statistics."""

    dataset_version: str = Field("training_v1", min_length=1)
    total_samples: int = Field(..., ge=0)
    train_samples: int = Field(..., ge=0)
    validation_samples: int = Field(..., ge=0)
    quarantine_samples: int = Field(..., ge=0)
    class_distribution: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Nested counts: {category: {split: count, total: N}}",
    )
    source_distribution: dict[str, int] = Field(default_factory=dict)
    group_count: int = Field(..., ge=0)
    multi_issue_count: int = Field(default=0, ge=0)
    quality_flags_summary: dict[str, int] = Field(default_factory=dict)
    leakage_check_summary: dict[str, int] = Field(default_factory=dict)
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat()
    )

    schema_version: str = Field("1.0.0", min_length=1)

    model_config = ConfigDict(from_attributes=True)
