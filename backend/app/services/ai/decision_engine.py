from typing import Any

from app.core.config import get_settings
from app.models.enums import PriorityLevel, SeverityLevel


class PrototypeDecisionEngine:
    """Policy-based decision engine producing category, severity, and review routing."""

    PRIORITY_LOOKUP = {
        SeverityLevel.CRITICAL: PriorityLevel.CRITICAL,
        SeverityLevel.HIGH: PriorityLevel.HIGH,
        SeverityLevel.MEDIUM: PriorityLevel.MEDIUM,
        SeverityLevel.LOW: PriorityLevel.LOW,
    }

    @property
    def confidence_threshold(self) -> float:
        return get_settings().AI_REVIEW_CONFIDENCE_THRESHOLD

    @property
    def agreement_threshold(self) -> float:
        return get_settings().AI_MODALITY_AGREEMENT_THRESHOLD

    def decide(
        self,
        vision_result: dict[str, Any],
        text_result: dict[str, Any],
        fusion_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Synthesize final recommendations and check verification policy gates."""
        # Check if modern probability fusion result is provided
        if "fused_category" in fusion_result and "fused_confidence" in fusion_result:
            final_category = fusion_result["fused_category"]
            overall_confidence = float(fusion_result["fused_confidence"])
            mod_agreement = fusion_result.get("modality_agreement")
            fallback_mode = fusion_result.get("fallback_mode", "MULTIMODAL")
            has_image = fallback_mode != "TEXT_ONLY"
            disagree_detected = bool(fusion_result.get("disagreement_detected", False))
        else:
            v_cat = vision_result.get("predicted_category")
            t_cat = text_result.get("predicted_category")
            v_conf = vision_result.get("confidence", 0.5)
            t_conf = text_result.get("confidence", 0.5)
            has_image = vision_result.get("has_image", False)
            mod_agreement = fusion_result.get("modality_agreement")
            disagree_detected = False

            # Decide category
            if t_cat and t_cat != "Other":
                final_category = t_cat
            elif v_cat and v_cat != "Other":
                final_category = v_cat
            else:
                final_category = "Other"

            # Overall confidence: weighted blend of text, vision, and agreement
            if has_image:
                mod_num = float(mod_agreement) if mod_agreement is not None else 0.50
                overall_confidence = round((t_conf * 0.45) + (v_conf * 0.35) + (mod_num * 0.20), 2)
                fallback_mode = "MULTIMODAL"
            else:
                overall_confidence = round(t_conf * 0.70, 2)
                fallback_mode = "TEXT_ONLY"

        # Suggested severity: pick the higher urgency signal for safety
        t_sev = text_result.get("predicted_severity", SeverityLevel.LOW)
        v_sev = vision_result.get("predicted_severity", SeverityLevel.LOW)

        sev_weights = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }
        if sev_weights.get(t_sev, 1) >= sev_weights.get(v_sev, 1):
            suggested_severity = t_sev
        else:
            suggested_severity = v_sev

        # Operational priority maps from severity with potential emergency override
        operational_priority = self.PRIORITY_LOOKUP.get(suggested_severity, PriorityLevel.MEDIUM)

        # Evaluate Review Requirement Policy Gates
        review_required = False
        review_reason = None
        decision_reasons = []

        if not has_image:
            review_required = True
            review_reason = "UNIMODAL_TEXT_FALLBACK"
            decision_reasons.append(
                "Report processed in unimodal text fallback mode "
                "(photographic evidence absent or invalid). "
                "0.70 policy penalty applied (administrative safety policy, "
                "not statistical probability). Verification required."
            )

        if overall_confidence < self.confidence_threshold:
            review_required = True
            if not review_reason:
                review_reason = "LOW_CONFIDENCE"
            decision_reasons.append(
                f"Confidence ({overall_confidence:.2f}) < "
                f"threshold ({self.confidence_threshold:.2f})."
            )

        if has_image and (
            disagree_detected
            or (mod_agreement is not None and mod_agreement < self.agreement_threshold)
        ):
            review_required = True
            review_reason = (
                "MODALITY_DISAGREEMENT"
                if not review_reason
                else f"{review_reason}_AND_DISAGREEMENT"
            )
            decision_reasons.append(
                f"Agreement ({mod_agreement:.2f}) indicates cross-modal contradiction."
                if mod_agreement is not None
                else "Cross-modal category discrepancy detected."
            )

        if final_category == "Other":
            review_required = True
            review_reason = "UNCLASSIFIED_ISSUE" if not review_reason else review_reason
            decision_reasons.append(
                "Defect does not match canonical civic categories; review required."
            )

        if not decision_reasons:
            decision_reasons.append(
                "Multimodal concordance and confidence metrics satisfy automatic triage threshold."
            )

        return {
            "suggested_category": final_category,
            "suggested_severity": suggested_severity,
            "operational_priority": operational_priority,
            "confidence": overall_confidence,
            "review_required": review_required,
            "review_reason": review_reason,
            "fallback_mode": fallback_mode,
            "decision_explanation": " | ".join(decision_reasons),
        }
