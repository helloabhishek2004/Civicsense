from typing import Any

from app.core.config import get_settings
from app.models.enums import PriorityLevel, SeverityLevel
from app.schemas.normalized_prediction import (
    CategoryPredictionItem,
    NormalizedPrediction,
    PredictionConfidenceTier,
)


class PredictionNormalizer:
    """Adapter transforming raw analyzer outputs into the canonical schema."""

    CATEGORY_LABELS: dict[str, str] = {
        "Pothole": "Pothole / Road Surface Cavity",
        "Garbage": "Solid Waste & Debris Accumulation",
        "Water Leakage": "Water Pipeline Leak & Fluid Pooling",
        "Streetlight": "Street Lighting & Luminaire Defect",
        "Road Damage": "Road Surface Crack & Fissure Pattern",
        "Drainage": "Stormwater Drainage & Clogged Sewer",
        "Infrastructure": "Damaged Public Footpath / Structure",
        "Other": "Unclassified Civic Issue",
    }

    @classmethod
    def get_category_label(cls, category: str) -> str:
        """Map canonical code to human-readable civic defect label."""
        return cls.CATEGORY_LABELS.get(category, f"Unclassified Issue ({category})")

    @classmethod
    def classify_confidence_tier(cls, confidence: float, category: str) -> PredictionConfidenceTier:
        """Enforce strict multi-tier confidence classification policy."""
        settings = get_settings()
        if category == "Other":
            return PredictionConfidenceTier.UNCERTAIN
        if confidence >= settings.AI_CONFIDENCE_HIGH_THRESHOLD:
            return PredictionConfidenceTier.HIGH
        elif confidence >= settings.AI_CONFIDENCE_MEDIUM_THRESHOLD:
            return PredictionConfidenceTier.MEDIUM
        elif confidence >= 0.50:
            return PredictionConfidenceTier.LOW
        else:
            return PredictionConfidenceTier.UNCERTAIN

    @classmethod
    def create_fallback_prediction(
        cls,
        reason: str = "Pipeline fallback",
        timing_breakdown: dict[str, int | float | None] | None = None,
        warnings: list[str] | None = None,
    ) -> NormalizedPrediction:
        """Construct a safe degraded prediction when model output is invalid or processing fails."""
        all_warnings = list(warnings or [])
        all_warnings.append(reason)
        return NormalizedPrediction(
            predicted_category="Other",
            category_label=cls.CATEGORY_LABELS["Other"],
            confidence=0.0,
            confidence_tier=PredictionConfidenceTier.FAILED,
            severity=SeverityLevel.LOW,
            priority=PriorityLevel.LOW,
            evidence_agreement=None,
            model_name="fallback_handler",
            model_version="1.5.0",
            inference_source="pipeline_fallback",
            inference_time_ms=0,
            requires_review=True,
            review_reasons=["PIPELINE_ERROR", reason],
            warnings=all_warnings,
            top_predictions=[
                CategoryPredictionItem(
                    category="Other",
                    label=cls.CATEGORY_LABELS["Other"],
                    confidence=0.0,
                )
            ],
            decision_explanation=f"Safe degraded fallback applied: {reason}",
            hardware_acceleration="NONE",
            timing_breakdown=timing_breakdown or {},
        )

    @classmethod
    def normalize(
        cls,
        raw_vision: dict[str, Any],
        raw_text: dict[str, Any],
        raw_fusion: dict[str, Any],
        raw_decision: dict[str, Any],
        inference_time_ms: int,
        inference_source: str = "server_rule_engine",
        model_name: str = "deterministic_demo_processor",
        model_version: str = "1.5.0",
        hardware_acceleration: str = "NONE",
        timing_breakdown: dict[str, int | float | None] | None = None,
        warnings: list[str] | None = None,
    ) -> NormalizedPrediction:
        """Create a canonical NormalizedPrediction instance with strict schema validation."""
        # Validate decision dict presence and required keys
        if not isinstance(raw_decision, dict):
            raise ValueError("Malformed model output: raw_decision must be a dictionary")

        if "confidence" not in raw_decision:
            raise ValueError("Malformed model output: missing 'confidence' key in decision result")

        conf_val = raw_decision["confidence"]
        try:
            float_conf = float(conf_val)
        except (ValueError, TypeError) as err:
            msg = f"Malformed model output: non-numeric confidence value '{conf_val}'"
            raise ValueError(msg) from err

        if float_conf < 0.0 or float_conf > 1.0:
            msg = (
                f"Malformed model output: confidence {float_conf} "
                "is outside allowable range [0.0, 1.0]"
            )
            raise ValueError(msg)
        confidence = round(float_conf, 2)

        if "suggested_category" not in raw_decision:
            raise ValueError(
                "Malformed model output: missing 'suggested_category' key in decision result"
            )

        category = raw_decision.get("suggested_category") or "Other"
        label = cls.get_category_label(category)

        # Validate fusion dict
        if not isinstance(raw_fusion, dict):
            raise ValueError("Malformed model output: raw_fusion must be a dictionary")

        if "modality_agreement" in raw_fusion and raw_fusion["modality_agreement"] is not None:
            try:
                float_agr = float(raw_fusion["modality_agreement"])
            except (ValueError, TypeError) as err:
                agr_val = raw_fusion["modality_agreement"]
                msg = f"Malformed model output: non-numeric agreement '{agr_val}'"
                raise ValueError(msg) from err
            if float_agr < 0.0 or float_agr > 1.0:
                msg = (
                    f"Malformed model output: modality_agreement {float_agr} is outside [0.0, 1.0]"
                )
                raise ValueError(msg)
            evidence_agreement: float | None = round(float_agr, 2)
        elif raw_vision.get("has_image"):
            evidence_agreement = 0.50
        else:
            # Single modality: do not claim or fabricate modality agreement
            evidence_agreement = None

        tier = cls.classify_confidence_tier(confidence, category)

        raw_sev = raw_decision.get("suggested_severity", SeverityLevel.MEDIUM)
        severity = (
            raw_sev if isinstance(raw_sev, SeverityLevel) else SeverityLevel(str(raw_sev).upper())
        )

        raw_pri = raw_decision.get("operational_priority", PriorityLevel.MEDIUM)
        priority = (
            raw_pri if isinstance(raw_pri, PriorityLevel) else PriorityLevel(str(raw_pri).upper())
        )

        requires_review = bool(raw_decision.get("review_required", False))
        review_reason = raw_decision.get("review_reason")
        review_reasons = [review_reason] if review_reason else []

        all_warnings = list(warnings or [])
        if inference_source == "unimodal_text_fallback":
            all_warnings.append("IMAGE_UNAVAILABLE_FALLBACK")
        if tier in (PredictionConfidenceTier.LOW, PredictionConfidenceTier.UNCERTAIN):
            all_warnings.append(f"CONFIDENCE_{tier.value}")
        if (
            evidence_agreement is not None
            and evidence_agreement < get_settings().AI_MODALITY_AGREEMENT_THRESHOLD
            and raw_vision.get("has_image")
        ):
            all_warnings.append("MODALITY_AGREEMENT_LOW")

        # Compile top predictions candidates
        top_preds = [
            CategoryPredictionItem(
                category=category,
                label=label,
                confidence=confidence,
            )
        ]
        # Include runner-up if distinct
        v_cat = raw_vision.get("predicted_category")
        if v_cat and v_cat != category and v_cat != "Other":
            v_conf = round(float(raw_vision.get("confidence", 0.5)), 2)
            top_preds.append(
                CategoryPredictionItem(
                    category=v_cat,
                    label=cls.get_category_label(v_cat),
                    confidence=min(0.99, v_conf),
                )
            )

        explanation = (
            raw_decision.get("decision_explanation")
            or "Provisional multimodal evaluation complete."
        )

        return NormalizedPrediction(
            predicted_category=category,
            category_label=label,
            confidence=confidence,
            confidence_tier=tier,
            severity=severity,
            priority=priority,
            evidence_agreement=evidence_agreement,
            model_name=model_name,
            model_version=model_version,
            inference_source=inference_source,
            inference_time_ms=max(0, inference_time_ms),
            requires_review=requires_review,
            review_reasons=review_reasons,
            warnings=all_warnings,
            top_predictions=top_preds,
            decision_explanation=explanation,
            hardware_acceleration=hardware_acceleration,
            timing_breakdown=timing_breakdown or {},
        )
