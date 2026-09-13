"""CivicSense Canonical Text Model Interface Architecture (Phase 4A).

Defines decoupled, production-grade interfaces for text defect classifiers:
- Universal TextModel interface returning normalized 6-class probability distributions
- Explicit outcome taxonomy separating true predictions from edge cases:
  1. SUCCESS: Valid model prediction with normalized probability distribution
  2. LOW_CONFIDENCE: Valid prediction where max probability is below operational threshold
  3. EMPTY_OR_INVALID_INPUT: Empty, whitespace-only, or degenerate text
  4. MODEL_UNAVAILABLE: Model files missing, uninitialized, or disabled via configuration
  5. INFERENCE_ERROR: Runtime exception handled safely without crashing
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CANONICAL_TEXT_CATEGORIES: list[str] = [
    "Pothole",
    "Road Damage",
    "Garbage",
    "Water Leakage",
    "Streetlight",
    "Other",
]


class TextModelStatus(str, Enum):
    """Readiness lifecycle status of a text inference model."""

    READY = "READY"
    UNAVAILABLE = "UNAVAILABLE"
    LOADING_FAILED = "LOADING_FAILED"
    DISABLED = "DISABLED"


class TextInferenceOutcome(str, Enum):
    """Explicit taxonomy of text classification outcomes."""

    SUCCESS = "SUCCESS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    EMPTY_OR_INVALID_INPUT = "EMPTY_OR_INVALID_INPUT"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    INFERENCE_ERROR = "INFERENCE_ERROR"


class TextModelMetadata(BaseModel):
    """Descriptive metadata and specifications for a text classifier."""

    model_name: str = Field(..., description="Unique model identifier")
    model_version: str = Field(..., description="Semantic version of model / weights")
    architecture_family: str = Field(
        ..., description="Architecture family (e.g. transformer, tfidf, rules)"
    )
    num_classes: int = Field(default=6, description="Number of canonical output categories")
    canonical_classes: list[str] = Field(
        default_factory=lambda: list(CANONICAL_TEXT_CATEGORIES),
        description="Canonical category ordering",
    )
    device: str = Field(default="cpu", description="Compute execution device (cpu)")
    runtime: str = Field(
        default="python",
        description="Inference runtime (pytorch_cpu, scikit_learn, prototype_rules)",
    )

    model_config = ConfigDict(frozen=True)


class TextPrediction(BaseModel):
    """Standardized output schema for all CivicSense text intelligence models."""

    predicted_category: str = Field(..., description="Top predicted canonical category")
    confidence: float = Field(
        ..., description="Confidence score associated with prediction [0.0, 1.0]"
    )
    probabilities: dict[str, float] = Field(
        ...,
        description="Normalized probability distribution across all 6 canonical categories",
    )
    status: TextInferenceOutcome = Field(
        default=TextInferenceOutcome.SUCCESS, description="Inference outcome status"
    )
    model_name: str = Field(..., description="Model identifier producing this prediction")
    model_version: str = Field(..., description="Version of model producing this prediction")
    inference_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Supplementary diagnostics, token counts, or latency stats",
    )

    model_config = ConfigDict(frozen=True)


class TextModel(ABC):
    """Universal abstract base class for all CivicSense text classifiers."""

    @abstractmethod
    def predict(self, text: str) -> TextPrediction:
        """Classify citizen issue text into canonical 6-class distribution."""
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self) -> TextModelMetadata:
        """Return model metadata and specifications."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> TextModelStatus:
        """Return readiness lifecycle status."""
        raise NotImplementedError
