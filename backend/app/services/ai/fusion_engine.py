import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SeverityLevel
from app.services.ai.real_vision_model import validate_class_probabilities
from app.services.ai.text_analyzer import (
    text_result_to_probabilities,
)
from app.services.ai.vision_interface import (
    CANONICAL_VISION_CATEGORIES,
    VisionInferenceOutcome,
    VisionPrediction,
)


class FusionConfig(BaseModel):
    """Configuration hyperparameters for multimodal probability fusion."""

    name: str = Field(default="vision_assisted", description="Identifier for fusion configuration")
    text_weight: float = Field(
        default=0.60, ge=0.0, le=1.0, description="Base weight assigned to text probability vector"
    )
    vision_weight: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Base weight assigned to vision probability vector",
    )
    disagreement_penalty: float = Field(
        default=0.15,
        ge=0.0,
        le=0.50,
        description="Confidence reduction penalty applied when modalities disagree",
    )
    temperature: float = Field(
        default=0.80, gt=0.0, description="Temperature scaling factor for confidence calibration"
    )
    confidence_adaptive: bool = Field(
        default=False,
        description="If True, weights dynamically adapt to relative modality confidence",
    )
    min_confidence_threshold: float = Field(
        default=0.60, ge=0.0, le=1.0, description="Minimum confidence for automatic triage"
    )
    review_agreement_threshold: float = Field(
        default=0.50, ge=0.0, le=1.0, description="Minimum modality agreement score"
    )

    model_config = ConfigDict(frozen=True)


class MultimodalFusionResult(BaseModel):
    """Rich structured result emitted by multimodal probability fusion."""

    fused_category: str = Field(..., description="Top-1 category resulting from probability fusion")
    fused_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Calibrated confidence score of top-1 fused category"
    )
    fused_probabilities: dict[str, float] = Field(
        ..., description="Complete 6-class calibrated probability distribution"
    )
    raw_probabilities: dict[str, float] = Field(
        ..., description="Unscaled pre-temperature probability distribution"
    )
    predicted_severity: SeverityLevel = Field(
        ..., description="Synthesized severity signal taking higher urgency"
    )
    modality_agreement: float = Field(
        ..., ge=0.0, le=1.0, description="Concordance score (cosine similarity) between modalities"
    )
    category_agreement: bool = Field(
        ..., description="True if text and vision top-1 categories match"
    )
    disagreement_detected: bool = Field(
        ..., description="True if modalities conflict in their primary category"
    )
    fallback_mode: str = Field(
        ..., description="Operational fallback status: MULTIMODAL, TEXT_ONLY, VISION_ONLY"
    )
    requires_review: bool = Field(
        ..., description="Whether human review is required according to triage policy gates"
    )
    review_reasons: list[str] = Field(
        default_factory=list, description="Explicit reasons triggering human verification"
    )
    effective_text_weight: float = Field(
        ..., ge=0.0, le=1.0, description="Actual normalized weight applied to text"
    )
    effective_vision_weight: float = Field(
        ..., ge=0.0, le=1.0, description="Actual normalized weight applied to vision"
    )
    conflict_reasons: list[str] = Field(
        default_factory=list, description="Diagnostic explanations of cross-modal conflict"
    )
    explanation: str = Field(..., description="Human-readable decision explanation")
    text_prediction: dict[str, Any] = Field(
        default_factory=dict, description="Summary of text modality input"
    )
    vision_prediction: dict[str, Any] = Field(
        default_factory=dict, description="Summary of vision modality input"
    )

    model_config = ConfigDict(from_attributes=True)


class MultimodalFusionEngine:
    """Production-grade transparent probability fusion engine with calibration and safety gates."""

    SEVERITY_ORDER: dict[SeverityLevel, int] = {
        SeverityLevel.LOW: 1,
        SeverityLevel.MEDIUM: 2,
        SeverityLevel.HIGH: 3,
        SeverityLevel.CRITICAL: 4,
    }

    def __init__(self, default_config: FusionConfig | None = None) -> None:
        self.default_config = default_config or FusionConfig()

    def fuse(
        self,
        vision_input: dict[str, Any] | VisionPrediction | None,
        text_input: dict[str, Any] | None,
        config: FusionConfig | None = None,
    ) -> MultimodalFusionResult:
        """Execute weighted probability fusion with calibrated temperature scaling."""
        cfg = config or self.default_config
        conflict_reasons: list[str] = []
        review_reasons: list[str] = []

        # Parse text modality
        has_text = bool(text_input and text_input.get("predicted_category"))
        t_cat = (text_input.get("predicted_category") or "Other") if text_input else "Other"
        t_conf = float(text_input.get("confidence", 0.45)) if text_input else 0.0
        t_sev = (
            text_input.get("predicted_severity", SeverityLevel.LOW)
            if text_input
            else SeverityLevel.LOW
        )
        if not isinstance(t_sev, SeverityLevel):
            t_sev = (
                SeverityLevel(t_sev)
                if t_sev in SeverityLevel._value2member_map_
                else SeverityLevel.LOW
            )

        if text_input and "class_probabilities" in text_input and text_input["class_probabilities"]:
            t_probs = dict(text_input["class_probabilities"])
        elif text_input:
            t_probs = text_result_to_probabilities(text_input)
        else:
            t_probs = {
                c: round(1.0 / len(CANONICAL_VISION_CATEGORIES), 4)
                for c in CANONICAL_VISION_CATEGORIES
            }

        # Parse vision modality
        if isinstance(vision_input, VisionPrediction):
            v_dict: dict[str, Any] = {
                "has_image": vision_input.outcome
                in (VisionInferenceOutcome.SUCCESS, VisionInferenceOutcome.LOW_CONFIDENCE),
                "predicted_category": vision_input.predicted_category,
                "confidence": vision_input.confidence,
                "class_probabilities": vision_input.class_probabilities,
                "outcome": vision_input.outcome.value,
                "predicted_severity": SeverityLevel.LOW,
                "error_message": vision_input.error_message,
            }
        elif isinstance(vision_input, dict):
            v_dict = vision_input
        else:
            v_dict = {
                "has_image": False,
                "predicted_category": None,
                "confidence": 0.0,
                "class_probabilities": {},
            }

        has_image = bool(v_dict.get("has_image", False))
        v_cat = v_dict.get("predicted_category")
        v_conf = float(v_dict.get("confidence", 0.0))
        v_probs = dict(v_dict.get("class_probabilities", {}))
        v_sev = v_dict.get("predicted_severity", SeverityLevel.LOW)
        if not isinstance(v_sev, SeverityLevel):
            v_sev = (
                SeverityLevel(v_sev)
                if v_sev in SeverityLevel._value2member_map_
                else SeverityLevel.LOW
            )

        # Validate vision probabilities if image is present
        v_valid = False
        if has_image and v_probs:
            is_valid, _ = validate_class_probabilities(v_probs)
            v_valid = is_valid

        # Case A: Vision is missing, failed, or corrupt -> FALLBACK TO TEXT_ONLY
        if not has_image or not v_valid:
            fallback_conf = round(t_conf * 0.70, 4)
            review_reasons.append("UNIMODAL_TEXT_FALLBACK")
            conflict_reasons.append(
                "Single modality execution: photographic evidence absent or invalid."
            )
            return MultimodalFusionResult(
                fused_category=t_cat,
                fused_confidence=fallback_conf,
                fused_probabilities=t_probs,
                raw_probabilities=t_probs,
                predicted_severity=t_sev,
                modality_agreement=0.0,
                category_agreement=False,
                disagreement_detected=False,
                fallback_mode="TEXT_ONLY",
                requires_review=True,
                review_reasons=review_reasons,
                effective_text_weight=1.0,
                effective_vision_weight=0.0,
                conflict_reasons=conflict_reasons,
                explanation=(
                    "Report processed in unimodal text fallback mode "
                    "(0.70x safety policy penalty). Verification required."
                ),
                text_prediction={"category": t_cat, "confidence": t_conf, "severity": t_sev.value},
                vision_prediction={
                    "status": "UNAVAILABLE_OR_INVALID",
                    "category": None,
                    "confidence": 0.0,
                },
            )

        # Case B: Text is missing -> FALLBACK TO VISION_ONLY
        if not has_text:
            fallback_conf = round(v_conf * 0.70, 4)
            review_reasons.append("UNIMODAL_VISION_FALLBACK")
            conflict_reasons.append(
                "Single modality execution: citizen textual description absent or empty."
            )
            return MultimodalFusionResult(
                fused_category=v_cat or "Other",
                fused_confidence=fallback_conf,
                fused_probabilities=v_probs,
                raw_probabilities=v_probs,
                predicted_severity=v_sev,
                modality_agreement=0.0,
                category_agreement=False,
                disagreement_detected=False,
                fallback_mode="VISION_ONLY",
                requires_review=True,
                review_reasons=review_reasons,
                effective_text_weight=0.0,
                effective_vision_weight=1.0,
                conflict_reasons=conflict_reasons,
                explanation=(
                    "Report processed in unimodal vision fallback mode "
                    "(0.70x safety policy penalty). Verification required."
                ),
                text_prediction={"status": "MISSING", "category": None, "confidence": 0.0},
                vision_prediction={
                    "category": v_cat,
                    "confidence": v_conf,
                    "severity": v_sev.value,
                },
            )


        # Case C: Both modalities present -> MULTIMODAL PROBABILITY FUSION
        if cfg.confidence_adaptive:
            tot_c = t_conf + v_conf
            if tot_c > 0:
                eff_wt = t_conf / tot_c
                eff_wv = v_conf / tot_c
            else:
                eff_wt = 0.50
                eff_wv = 0.50
        else:
            tot_w = cfg.text_weight + cfg.vision_weight
            eff_wt = cfg.text_weight / tot_w if tot_w > 0 else 0.50
            eff_wv = cfg.vision_weight / tot_w if tot_w > 0 else 0.50

        # Weighted combination of posterior probabilities
        raw_fused: dict[str, float] = {}
        for c in CANONICAL_VISION_CATEGORIES:
            raw_fused[c] = (eff_wt * t_probs.get(c, 0.0)) + (eff_wv * v_probs.get(c, 0.0))

        # Temperature Scaling Calibration
        T = cfg.temperature
        if abs(T - 1.0) > 1e-4:
            log_p = {c: math.log(max(1e-7, p)) / T for c, p in raw_fused.items()}
            max_log_p = max(log_p.values())
            exp_p = {c: math.exp(v - max_log_p) for c, v in log_p.items()}
            sum_exp = sum(exp_p.values())
            calib_fused = {c: exp_p[c] / sum_exp for c in exp_p}
        else:
            tot_f = sum(raw_fused.values())
            calib_fused = {c: p / tot_f for c, p in raw_fused.items()}

        best_cat = max(calib_fused.keys(), key=lambda c: calib_fused[c])
        fused_conf = calib_fused[best_cat]

        # Calculate Modality Concordance (Cosine Similarity)
        dot = sum(t_probs.get(c, 0.0) * v_probs.get(c, 0.0) for c in CANONICAL_VISION_CATEGORIES)
        norm_t = math.sqrt(sum(p * p for p in t_probs.values()))
        norm_v = math.sqrt(sum(p * p for p in v_probs.values()))
        cos_sim = round(dot / (norm_t * norm_v) if (norm_t * norm_v) > 0 else 0.0, 4)

        cat_agree = t_cat == v_cat
        disagree_detected = not cat_agree

        if not cat_agree:
            conflict_reasons.append(
                f"Category discrepancy: Text indicates '{t_cat}' ({t_conf:.2f}) "
                f"vs Vision '{v_cat}' ({v_conf:.2f})."
            )
            # Apply disagreement penalty
            fused_conf = max(0.10, fused_conf - cfg.disagreement_penalty)
            review_reasons.append("MODALITY_DISAGREEMENT")

        # Synthesize severity taking higher urgency
        if self.SEVERITY_ORDER.get(t_sev, 1) >= self.SEVERITY_ORDER.get(v_sev, 1):
            syn_sev = t_sev
        else:
            syn_sev = v_sev

        # Check operational review thresholds
        if fused_conf < cfg.min_confidence_threshold:
            review_reasons.append("LOW_CONFIDENCE")
        if best_cat == "Other":
            review_reasons.append("UNCLASSIFIED_ISSUE")
        if cos_sim < cfg.review_agreement_threshold:
            if "MODALITY_DISAGREEMENT" not in review_reasons:
                review_reasons.append("LOW_MODALITY_CONCORDANCE")

        requires_review = len(review_reasons) > 0

        # Explanation
        if not requires_review:
            explanation = (
                f"High-confidence multimodal consensus: '{best_cat}' (confidence {fused_conf:.2f}, "
                f"concordance {cos_sim:.2f}). Satisfies automatic triage threshold."
            )
        else:
            reasons_str = ", ".join(review_reasons)
            explanation = (
                f"Multimodal review queued ({reasons_str}): predicted '{best_cat}' "
                f"(confidence {fused_conf:.2f}, concordance {cos_sim:.2f}). "
                f"Awaiting officer triage."
            )

        return MultimodalFusionResult(
            fused_category=best_cat,
            fused_confidence=round(fused_conf, 4),
            fused_probabilities={c: round(calib_fused[c], 4) for c in CANONICAL_VISION_CATEGORIES},
            raw_probabilities={c: round(raw_fused[c], 4) for c in CANONICAL_VISION_CATEGORIES},
            predicted_severity=syn_sev,
            modality_agreement=cos_sim,
            category_agreement=cat_agree,
            disagreement_detected=disagree_detected,
            fallback_mode="MULTIMODAL",
            requires_review=requires_review,
            review_reasons=review_reasons,
            effective_text_weight=round(eff_wt, 4),
            effective_vision_weight=round(eff_wv, 4),
            conflict_reasons=conflict_reasons,
            explanation=explanation,
            text_prediction={"category": t_cat, "confidence": t_conf, "severity": t_sev.value},
            vision_prediction={"category": v_cat, "confidence": v_conf, "severity": v_sev.value},
        )


class PrototypeFusionEngine:
    """Combines outputs from prototype vision and text analyzers to compute modality agreement."""

    ENGINE_NAME = "Prototype Multimodal Fusion Layer"

    SEVERITY_WEIGHTS = {
        SeverityLevel.LOW: 1,
        SeverityLevel.MEDIUM: 2,
        SeverityLevel.HIGH: 3,
        SeverityLevel.CRITICAL: 4,
    }

    def __init__(self) -> None:
        self._modern_engine = MultimodalFusionEngine()

    def fuse(self, vision_result: dict[str, Any], text_result: dict[str, Any]) -> dict[str, Any]:
        """Cross-evaluate vision and text signals."""
        has_image = vision_result.get("has_image", False)
        v_cat = vision_result.get("predicted_category")
        t_cat = text_result.get("predicted_category")
        v_sev = vision_result.get("predicted_severity")
        t_sev = text_result.get("predicted_severity")

        conflict_reasons: list[str] = []

        if not has_image:
            return {
                "engine": self.ENGINE_NAME,
                "category_agreement": None,
                "severity_agreement": None,
                "modality_agreement": None,
                "conflict_reasons": [
                    "Single modality execution: No image evidence provided to verify text signals."
                ],
                "cross_modal_notes": (
                    "Unimodal fallback on textual signal. Modality agreement not applicable."
                ),
            }

        # Category agreement
        cat_agree = v_cat == t_cat
        if not cat_agree:
            conflict_reasons.append(
                f"Category mismatch: Vision indicates '{v_cat}' vs Text '{t_cat}'."
            )

        # Severity agreement
        v_weight = self.SEVERITY_WEIGHTS.get(v_sev, 2) if isinstance(v_sev, SeverityLevel) else 2
        t_weight = self.SEVERITY_WEIGHTS.get(t_sev, 2) if isinstance(t_sev, SeverityLevel) else 2
        sev_diff = abs(v_weight - t_weight)
        sev_agree = sev_diff == 0
        if not sev_agree:
            conflict_reasons.append(
                f"Severity discrepancy: Vision ({getattr(v_sev, 'value', v_sev)}) "
                f"vs Text ({getattr(t_sev, 'value', t_sev)})."
            )

        # Calculate overall modality agreement score
        score = 0.0
        if cat_agree:
            score += 0.60
        else:
            if v_cat == "Other" or t_cat == "Other":
                score += 0.25

        if sev_agree:
            score += 0.40
        elif sev_diff == 1:
            score += 0.20

        modality_agreement = round(min(1.0, max(0.10, score)), 2)

        return {
            "engine": self.ENGINE_NAME,
            "category_agreement": cat_agree,
            "severity_agreement": sev_agree,
            "modality_agreement": modality_agreement,
            "conflict_reasons": conflict_reasons,
            "cross_modal_notes": "Multimodal concordance evaluated."
            if not conflict_reasons
            else "Conflicting signals detected.",
        }
