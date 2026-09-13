"""CivicSense Vision Model Interface Architecture (Phase 3.3.1).

Defines decoupled, canonical interfaces for visual defect classifiers:
- Explicit separation between true 'Other' predictions and failure modes:
  1. Real model prediction of Other (valid classification of out-of-taxonomy defects)
  2. Model unavailable (weights missing, runtime uninstalled, disabled via config)
  3. Model loading failure (corrupted checkpoint, initialization crash)
  4. Image preprocessing failure (invalid format, corrupted bytes, decompression bomb)
  5. Inference failure (runtime tensor error, shape mismatch, NaN/inf output)
  6. Low-confidence prediction (valid softmax distribution where max probability < threshold)
- Decoupled from specific machine learning runtimes (PyTorch, ONNX Runtime, TFLite).
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CANONICAL_VISION_CATEGORIES: list[str] = [
    "Pothole",
    "Road Damage",
    "Garbage",
    "Water Leakage",
    "Streetlight",
    "Other",
]


class VisionModelStatus(str, Enum):
    """Lifecycle and readiness status of a visual inference model."""

    READY = "READY"
    UNAVAILABLE = "UNAVAILABLE"
    LOADING_FAILED = "LOADING_FAILED"
    DISABLED = "DISABLED"


class VisionInferenceOutcome(str, Enum):
    """Explicit taxonomy of visual inference outcomes."""

    SUCCESS = "SUCCESS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PREPROCESSING_ERROR = "PREPROCESSING_ERROR"
    INFERENCE_ERROR = "INFERENCE_ERROR"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"


class VisionModelMetadata(BaseModel):
    """Descriptive metadata and runtime specifications for a visual classifier."""

    model_name: str = Field(..., description="Unique model identifier (e.g. mobilenet_v3_small)")
    model_version: str = Field(..., description="Semantic version of model weights (e.g. 1.0.0)")
    architecture_family: str = Field(..., description="Neural network architecture family")
    input_resolution: tuple[int, int] = Field(
        default=(224, 224), description="Expected (width, height)"
    )
    num_classes: int = Field(default=6, description="Number of output categories")
    canonical_classes: list[str] = Field(
        default_factory=lambda: list(CANONICAL_VISION_CATEGORIES),
        description="List of canonical categories in output logits order",
    )
    device: str = Field(default="cpu", description="Compute execution device (cpu, cuda, edge)")
    runtime: str = Field(
        default="pytorch_cpu",
        description="Inference runtime (pytorch_cpu, onnxruntime_cpu, tflite, prototype)",
    )
    quantization: str = Field(
        default="none", description="Quantization precision (none, int8, fp16)"
    )

    model_config = ConfigDict(frozen=True)


class VisionPrediction(BaseModel):
    """Decoupled prediction contract produced by any visual model."""

    outcome: VisionInferenceOutcome = Field(
        ..., description="Explicit outcome category distinguishing success from error states"
    )
    predicted_category: str | None = Field(
        default=None,
        description=(
            "Canonical defect category if inference succeeded; None if error or unavailable"
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model confidence or top softmax probability (0.0 on error)",
    )
    class_probabilities: dict[str, float] = Field(
        default_factory=dict,
        description="Normalized posterior probabilities for all canonical classes",
    )
    model_name: str = Field(..., description="Name of model that produced this prediction")
    model_version: str = Field(..., description="Version of model weights used")
    inference_time_ms: float = Field(
        ge=0.0, description="Measured forward-pass inference duration in milliseconds"
    )
    preprocessing_time_ms: float = Field(
        ge=0.0, description="Measured image preprocessing/decoding duration in milliseconds"
    )
    requires_review: bool = Field(
        default=True,
        description="Administrative flag indicating human verification is required",
    )
    error_message: str | None = Field(
        default=None, description="Diagnostic error explanation if outcome is not SUCCESS"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Model-specific diagnostic features, intermediate activations, or telemetry",
    )

    model_config = ConfigDict(from_attributes=True)


class VisionModel(ABC):
    """Abstract interface defining the visual inference contract."""

    @property
    @abstractmethod
    def metadata(self) -> VisionModelMetadata:
        """Return model metadata and runtime specifications."""
        ...

    @property
    @abstractmethod
    def status(self) -> VisionModelStatus:
        """Return current model operational readiness."""
        ...

    @abstractmethod
    def predict(self, image_bytes: bytes) -> VisionPrediction:
        """Execute single-image inference against raw image bytes."""
        ...

    def predict_batch(self, image_bytes_list: list[bytes]) -> list[VisionPrediction]:
        """Execute batch inference. Default implementation invokes predict iteratively."""
        return [self.predict(img) for img in image_bytes_list]


class PrototypeVisionModel(VisionModel):
    """Adapter wrapping the Phase 1.5 deterministic prototype analyzer into the modern interface."""

    def __init__(self, confidence_threshold: float = 0.70) -> None:
        self.confidence_threshold = confidence_threshold
        self._metadata = VisionModelMetadata(
            model_name="prototype_vision_analyzer",
            model_version="1.5.0",
            architecture_family="RuleBasedMetadataPrior",
            input_resolution=(224, 224),
            num_classes=6,
            canonical_classes=list(CANONICAL_VISION_CATEGORIES),
            device="cpu",
            runtime="prototype",
            quantization="none",
        )
        self._status = VisionModelStatus.READY

    @property
    def metadata(self) -> VisionModelMetadata:
        return self._metadata

    @property
    def status(self) -> VisionModelStatus:
        return self._status

    def predict(self, image_bytes: bytes) -> VisionPrediction:
        import io
        import time

        from PIL import Image

        prep_start = time.perf_counter()

        if not image_bytes:
            return VisionPrediction(
                outcome=VisionInferenceOutcome.PREPROCESSING_ERROR,
                predicted_category=None,
                confidence=0.0,
                class_probabilities={},
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=0.0,
                preprocessing_time_ms=0.0,
                requires_review=True,
                error_message="Image bytes buffer is empty or missing.",
            )

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img.verify()
        except Exception as err:
            prep_dur = round((time.perf_counter() - prep_start) * 1000, 2)
            return VisionPrediction(
                outcome=VisionInferenceOutcome.PREPROCESSING_ERROR,
                predicted_category=None,
                confidence=0.0,
                class_probabilities={},
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=0.0,
                preprocessing_time_ms=prep_dur,
                requires_review=True,
                error_message=f"Image decoding failed: {err}",
            )

        prep_dur = round((time.perf_counter() - prep_start) * 1000, 2)
        inf_start = time.perf_counter()

        # Prototype fallback logic: in production mode, returns 'Other' with 0.50 prior
        pred_cat = "Other"
        conf = 0.50
        inf_dur = round((time.perf_counter() - inf_start) * 1000, 2)

        # Distribute remaining probability evenly across classes to model uninformative prior
        uniform_rest = round((1.0 - conf) / 5.0, 4)
        probs = {c: uniform_rest for c in CANONICAL_VISION_CATEGORIES if c != pred_cat}
        probs[pred_cat] = conf

        is_low_conf = conf < self.confidence_threshold
        outcome = (
            VisionInferenceOutcome.LOW_CONFIDENCE if is_low_conf else VisionInferenceOutcome.SUCCESS
        )

        return VisionPrediction(
            outcome=outcome,
            predicted_category=pred_cat,
            confidence=conf,
            class_probabilities=probs,
            model_name=self._metadata.model_name,
            model_version=self._metadata.model_version,
            inference_time_ms=inf_dur,
            preprocessing_time_ms=prep_dur,
            requires_review=True,  # 0.50 is always below 0.70 threshold
            metadata={"prototype_prior_mode": "neutral_unclassified_image_baseline"},
        )


class MockVisionModel(VisionModel):
    """Test double allowing controlled simulation of all 6 vision outcomes."""

    def __init__(
        self,
        simulated_status: VisionModelStatus = VisionModelStatus.READY,
        forced_outcome: VisionInferenceOutcome | None = None,
        forced_category: str | None = "Pothole",
        forced_confidence: float = 0.88,
        forced_error: str | None = None,
    ) -> None:
        self._status = simulated_status
        self.forced_outcome = forced_outcome
        self.forced_category = forced_category
        self.forced_confidence = forced_confidence
        self.forced_error = forced_error
        self._metadata = VisionModelMetadata(
            model_name="mock_vision_classifier",
            model_version="0.1.0-test",
            architecture_family="MockSimulation",
            input_resolution=(224, 224),
            num_classes=6,
            canonical_classes=list(CANONICAL_VISION_CATEGORIES),
            device="cpu",
            runtime="mock",
            quantization="none",
        )

    @property
    def metadata(self) -> VisionModelMetadata:
        return self._metadata

    @property
    def status(self) -> VisionModelStatus:
        return self._status

    def predict(self, image_bytes: bytes) -> VisionPrediction:
        # 1. Model unavailable / loading failed checks
        if self._status != VisionModelStatus.READY:
            return VisionPrediction(
                outcome=VisionInferenceOutcome.MODEL_UNAVAILABLE,
                predicted_category=None,
                confidence=0.0,
                class_probabilities={},
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=0.0,
                preprocessing_time_ms=0.0,
                requires_review=True,
                error_message=self.forced_error
                or f"Model is not ready (status: {self._status.value}).",
            )

        # 2. Forced outcome simulation
        if self.forced_outcome == VisionInferenceOutcome.PREPROCESSING_ERROR:
            return VisionPrediction(
                outcome=VisionInferenceOutcome.PREPROCESSING_ERROR,
                predicted_category=None,
                confidence=0.0,
                class_probabilities={},
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=0.0,
                preprocessing_time_ms=1.5,
                requires_review=True,
                error_message=self.forced_error or "Simulated preprocessing failure.",
            )

        if self.forced_outcome == VisionInferenceOutcome.INFERENCE_ERROR:
            return VisionPrediction(
                outcome=VisionInferenceOutcome.INFERENCE_ERROR,
                predicted_category=None,
                confidence=0.0,
                class_probabilities={},
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=3.2,
                preprocessing_time_ms=1.5,
                requires_review=True,
                error_message=self.forced_error or "Simulated forward pass crash.",
            )

        if self.forced_outcome == VisionInferenceOutcome.LOW_CONFIDENCE:
            probs = {c: 0.1667 for c in CANONICAL_VISION_CATEGORIES}
            if self.forced_category and self.forced_category in probs:
                probs[self.forced_category] = self.forced_confidence
            return VisionPrediction(
                outcome=VisionInferenceOutcome.LOW_CONFIDENCE,
                predicted_category=self.forced_category,
                confidence=self.forced_confidence,
                class_probabilities=probs,
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=5.0,
                preprocessing_time_ms=1.5,
                requires_review=True,
            )

        # 3. Default clean success
        cat = self.forced_category or "Pothole"
        rem_p = round((1.0 - self.forced_confidence) / 5.0, 4)
        probs = {c: rem_p for c in CANONICAL_VISION_CATEGORIES}
        probs[cat] = self.forced_confidence
        return VisionPrediction(
            outcome=VisionInferenceOutcome.SUCCESS,
            predicted_category=cat,
            confidence=self.forced_confidence,
            class_probabilities=probs,
            model_name=self._metadata.model_name,
            model_version=self._metadata.model_version,
            inference_time_ms=8.5,
            preprocessing_time_ms=1.2,
            requires_review=(self.forced_confidence < 0.70 or cat == "Other"),
        )
