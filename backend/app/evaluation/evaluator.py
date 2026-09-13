import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from app.models.evidence import Evidence

from app.models.enums import EvidenceType
from app.schemas.normalized_prediction import NormalizedPrediction
from app.services.ai.decision_engine import PrototypeDecisionEngine
from app.services.ai.fusion_engine import PrototypeFusionEngine
from app.services.ai.input_validator import InputValidator
from app.services.ai.normalized_prediction import PredictionNormalizer
from app.services.ai.text_analyzer import PrototypeTextPatternAnalyzer
from app.services.ai.vision_analyzer import PrototypeVisionAnalyzer


@dataclass
class _OfflineEvidenceAdapter:
    """Lightweight in-memory adapter mimicking Evidence entity for PrototypeVisionAnalyzer."""

    evidence_type: EvidenceType = EvidenceType.IMAGE
    storage_uri: str = "offline://memory_buffer.jpg"
    mime_type: str = "image/jpeg"
    file_size_bytes: int = 0
    file_hash: str = ""
    metadata_json: dict[str, Any] = field(default_factory=dict)


class OfflineDeterministicEvaluator:
    """Headless, offline evaluator wrapping the deterministic pipeline sub-services.

    Executes without FastAPI, PostgreSQL, or network connections.
    """

    def __init__(self) -> None:
        self.vision_analyzer = PrototypeVisionAnalyzer()
        self.text_analyzer = PrototypeTextPatternAnalyzer()
        self.fusion_engine = PrototypeFusionEngine()
        self.decision_engine = PrototypeDecisionEngine()

    def evaluate(
        self,
        image_bytes: bytes | None = None,
        text: str | None = None,
    ) -> NormalizedPrediction:
        """Evaluate raw image bytes and/or text description offline.

        Returns canonical NormalizedPrediction instance with measured latency.
        """
        start_time = time.perf_counter()
        timing: dict[str, int | float | None] = {
            "intake_validation_ms": None,
            "vision_inference_ms": None,
            "text_inference_ms": None,
            "fusion_ms": None,
            "decision_ms": None,
        }
        warnings: list[str] = []

        # 1. Intake Validation
        intake_start = time.perf_counter()
        valid_image_result = None
        cleaned_text: str | None = None

        if image_bytes is not None and len(image_bytes) > 0:
            try:
                valid_image_result = InputValidator.validate_image_bytes(image_bytes)
            except Exception as err:
                warnings.append(f"IMAGE_VALIDATION_ERROR: {err}")

        if text is not None and text.strip():
            try:
                valid_text_result = InputValidator.validate_and_sanitize_text(text)
                cleaned_text = valid_text_result.cleaned_text
                warnings.extend(valid_text_result.warnings)
            except Exception as err:
                warnings.append(f"TEXT_VALIDATION_ERROR: {err}")

        timing["intake_validation_ms"] = round(
            max(0.0, (time.perf_counter() - intake_start) * 1000), 2
        )

        # 2. Vision Analysis
        v_start = time.perf_counter()
        if valid_image_result is not None:
            adapter = _OfflineEvidenceAdapter(
                evidence_type=EvidenceType.IMAGE,
                storage_uri="offline://evaluation_sample.jpg",
                mime_type=valid_image_result.mime_type,
                file_size_bytes=valid_image_result.file_size_bytes,
                file_hash=valid_image_result.sha256,
                metadata_json={},
            )
            raw_vision = self.vision_analyzer.analyze(
                cast(list["Evidence"], [adapter])
            )
            timing["vision_inference_ms"] = round(
                max(0.0, (time.perf_counter() - v_start) * 1000), 2
            )
        else:
            raw_vision = {
                "engine": self.vision_analyzer.ENGINE_NAME,
                "mode": self.vision_analyzer.MODE,
                "has_image": False,
                "predicted_category": None,
                "predicted_severity": "LOW",
                "confidence": 0.30,
                "features": {"image_count": 0, "image_quality": "missing"},
                "limitations": ["No image evidence provided or image validation failed."],
            }
            timing["vision_inference_ms"] = None

        # 3. Text Analysis
        t_start = time.perf_counter()
        if cleaned_text:
            raw_text = self.text_analyzer.analyze(cleaned_text)
            timing["text_inference_ms"] = round(
                max(0.0, (time.perf_counter() - t_start) * 1000), 2
            )
        else:
            raw_text = {
                "engine": self.text_analyzer.ENGINE_NAME,
                "mode": self.text_analyzer.MODE,
                "predicted_category": "Other",
                "predicted_severity": "LOW",
                "confidence": 0.50,
                "urgency_detected": False,
                "matched_keywords": [],
                "urgency_signals": [],
            }
            timing["text_inference_ms"] = None

        # 4. Fusion
        f_start = time.perf_counter()
        raw_fusion = self.fusion_engine.fuse(raw_vision, raw_text)
        timing["fusion_ms"] = round(max(0.0, (time.perf_counter() - f_start) * 1000), 2)

        # 5. Decision
        d_start = time.perf_counter()
        raw_decision = self.decision_engine.decide(raw_vision, raw_text, raw_fusion)
        timing["decision_ms"] = round(max(0.0, (time.perf_counter() - d_start) * 1000), 2)

        # 6. Normalization
        total_latency_ms = int((time.perf_counter() - start_time) * 1000)
        source = "offline_multimodal" if valid_image_result else "offline_unimodal_text"

        return PredictionNormalizer.normalize(
            raw_vision=raw_vision,
            raw_text=raw_text,
            raw_fusion=raw_fusion,
            raw_decision=raw_decision,
            inference_time_ms=max(0, total_latency_ms),
            inference_source=source,
            model_name="deterministic_demo_processor",
            model_version="1.5.0",
            hardware_acceleration="NONE",
            timing_breakdown=timing,
            warnings=warnings,
        )
