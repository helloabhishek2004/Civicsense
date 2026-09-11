from typing import Any

from app.models.enums import PriorityLevel, SeverityLevel


class PrototypeDecisionEngine:
    """Policy-based decision engine producing category, severity, and review routing."""

    CONFIDENCE_THRESHOLD = 0.70
    AGREEMENT_THRESHOLD = 0.60

    PRIORITY_LOOKUP = {
        SeverityLevel.CRITICAL: PriorityLevel.CRITICAL,
        SeverityLevel.HIGH: PriorityLevel.HIGH,
        SeverityLevel.MEDIUM: PriorityLevel.MEDIUM,
        SeverityLevel.LOW: PriorityLevel.LOW,
    }

    def decide(
        self,
        vision_result: dict[str, Any],
        text_result: dict[str, Any],
        fusion_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Synthesize final recommendations and check verification policy gates."""
        v_cat = vision_result.get("predicted_category")
        t_cat = text_result.get("predicted_category")
        v_conf = vision_result.get("confidence", 0.5)
        t_conf = text_result.get("confidence", 0.5)
        mod_agreement = fusion_result.get("modality_agreement", 0.5)

        # Decide category
        if t_cat and t_cat != "Other":
            final_category = t_cat
        elif v_cat and v_cat != "Other":
            final_category = v_cat
        else:
            final_category = "Other"

        # Overall confidence: weighted blend of text, vision, and agreement
        if vision_result.get("has_image", False):
            overall_confidence = round(
                (t_conf * 0.45) + (v_conf * 0.35) + (mod_agreement * 0.20), 2
            )
        else:
            overall_confidence = round(t_conf * 0.85, 2)  # Penalty for missing visual corroboration

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

        if overall_confidence < self.CONFIDENCE_THRESHOLD:
            review_required = True
            review_reason = "LOW_CONFIDENCE"
            decision_reasons.append(
                f"Confidence ({overall_confidence:.2f}) < threshold ({self.CONFIDENCE_THRESHOLD})."
            )

        if mod_agreement < self.AGREEMENT_THRESHOLD and vision_result.get("has_image", False):
            review_required = True
            review_reason = (
                "MODALITY_DISAGREEMENT"
                if not review_reason
                else f"{review_reason}_AND_DISAGREEMENT"
            )
            decision_reasons.append(
                f"Agreement ({mod_agreement:.2f}) indicates cross-modal contradiction."
            )

        if final_category == "Other":
            review_required = True
            review_reason = "UNCLASSIFIED_ISSUE" if not review_reason else review_reason
            decision_reasons.append(
                "Defect does not match canonical civic categories; review required."
            )

        if not vision_result.get("has_image", False):
            decision_reasons.append(
                "Report without photographic evidence. Verification recommended prior to dispatch."
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
            "decision_explanation": " | ".join(decision_reasons),
        }
