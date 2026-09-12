from typing import Any

from app.models.enums import SeverityLevel


class PrototypeFusionEngine:
    """Combines outputs from prototype vision and text analyzers to compute modality agreement."""

    ENGINE_NAME = "Prototype Multimodal Fusion Layer"

    SEVERITY_WEIGHTS = {
        SeverityLevel.LOW: 1,
        SeverityLevel.MEDIUM: 2,
        SeverityLevel.HIGH: 3,
        SeverityLevel.CRITICAL: 4,
    }

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
                "modality_agreement": 0.50,
                "conflict_reasons": [
                    "Single modality execution: No image evidence provided to verify text signals."
                ],
                "cross_modal_notes": "Unimodal fallback on textual signal.",
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
            # Partial credit if one is "Other"
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
