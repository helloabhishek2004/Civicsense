from typing import Any

from app.core.config import get_settings
from app.models.enums import SeverityLevel
from app.models.evidence import Evidence


class PrototypeVisionAnalyzer:
    """Deterministic prototype vision analyzer.

    DISCLAIMER: This is a clearly labeled rule-based feature extractor and metadata inspector,
    NOT a trained deep neural network. Used for demonstrable pipeline simulation.
    Filename stems do NOT affect classification unless explicitly enabled
    via prototype configuration.
    """

    ENGINE_NAME = "Prototype Vision Analyzer (Metadata & Heuristics)"
    MODE = "demo"

    def analyze(self, evidences: list[Evidence]) -> dict[str, Any]:
        """Analyze attached image evidences deterministically."""
        image_evidences = [ev for ev in evidences if ev.evidence_type.value == "IMAGE"]

        if not image_evidences:
            return {
                "engine": self.ENGINE_NAME,
                "mode": self.MODE,
                "has_image": False,
                "predicted_category": None,
                "predicted_severity": SeverityLevel.LOW,
                "confidence": 0.30,
                "features": {
                    "image_count": 0,
                    "image_quality": "missing",
                    "surface_damage_signal": "absent",
                },
                "limitations": [
                    "No image evidence attached to report.",
                    "Vision pipeline skipped visual feature inference.",
                ],
            }

        primary = image_evidences[0]
        meta = primary.metadata_json or {}
        settings = get_settings()

        # 1. Check explicitly labeled prototype simulation metadata first
        simulated_cat = (
            meta.get("prototype_category")
            or meta.get("simulated_category")
            or meta.get("visual_category")
        )

        category: str | None = None
        severity = SeverityLevel.LOW
        confidence = 0.50
        surface_damage = "unclassified_surface_feature"
        heuristic_source = "neutral_baseline"

        if simulated_cat and isinstance(simulated_cat, str):
            sim_lower = simulated_cat.lower()
            heuristic_source = "explicit_prototype_metadata"
            if any(w in sim_lower for w in ["pothole", "crater", "tarmac", "asphalt"]):
                category = "Pothole"
                severity = SeverityLevel.HIGH
                confidence = 0.84
                surface_damage = "detected_pothole_cavity"
            elif any(w in sim_lower for w in ["garbage", "waste", "trash", "dump", "debris"]):
                category = "Garbage"
                severity = SeverityLevel.MEDIUM
                confidence = 0.82
                surface_damage = "detected_waste_accumulation"
            elif any(w in sim_lower for w in ["water", "leak", "pipe", "overflow", "drain"]):
                category = "Water Leakage"
                severity = SeverityLevel.HIGH
                confidence = 0.79
                surface_damage = "detected_fluid_pooling"
            elif any(w in sim_lower for w in ["streetlight", "light", "lamp", "pole", "dark"]):
                category = "Streetlight"
                severity = SeverityLevel.LOW
                confidence = 0.76
                surface_damage = "detected_luminaire_defect"
            elif any(w in sim_lower for w in ["road", "crack", "pavement"]):
                category = "Road Damage"
                severity = SeverityLevel.MEDIUM
                confidence = 0.78
                surface_damage = "detected_fissure_pattern"
            else:
                category = simulated_cat.title()
                severity = SeverityLevel.MEDIUM
                confidence = 0.75
                surface_damage = "simulated_custom_defect"
        else:
            # 2. Check if legacy filename heuristics are explicitly enabled via prototype setting
            allow_filename = getattr(settings, "AI_ENABLE_FILENAME_HEURISTICS", False) or bool(
                meta.get("allow_prototype_filename_heuristics", False)
            )
            uri_lower = (primary.storage_uri or "").lower()

            if allow_filename and uri_lower:
                heuristic_source = "prototype_filename_stem"
                if any(w in uri_lower for w in ["pothole", "crater", "tarmac", "asphalt"]):
                    category = "Pothole"
                    severity = SeverityLevel.HIGH
                    confidence = 0.84
                    surface_damage = "detected_pothole_cavity"
                elif any(w in uri_lower for w in ["garbage", "waste", "trash", "dump", "debris"]):
                    category = "Garbage"
                    severity = SeverityLevel.MEDIUM
                    confidence = 0.82
                    surface_damage = "detected_waste_accumulation"
                elif any(w in uri_lower for w in ["water", "leak", "pipe", "overflow", "drain"]):
                    category = "Water Leakage"
                    severity = SeverityLevel.HIGH
                    confidence = 0.79
                    surface_damage = "detected_fluid_pooling"
                elif any(w in uri_lower for w in ["streetlight", "light", "lamp", "pole", "dark"]):
                    category = "Streetlight"
                    severity = SeverityLevel.LOW
                    confidence = 0.76
                    surface_damage = "detected_luminaire_defect"
                elif any(w in uri_lower for w in ["road", "crack", "pavement"]):
                    category = "Road Damage"
                    severity = SeverityLevel.MEDIUM
                    confidence = 0.78
                    surface_damage = "detected_fissure_pattern"
                else:
                    category = "Other"
                    severity = SeverityLevel.LOW
                    confidence = 0.52
                    surface_damage = "unclassified_surface_feature"
            else:
                # 3. Safe production baseline: filename stems NEVER affect classification
                category = "Other"
                severity = SeverityLevel.LOW
                confidence = 0.50
                surface_damage = "unclassified_surface_feature"
                heuristic_source = "unclassified_image_baseline"

        return {
            "engine": self.ENGINE_NAME,
            "mode": self.MODE,
            "has_image": True,
            "predicted_category": category,
            "predicted_severity": severity,
            "confidence": confidence,
            "features": {
                "image_count": len(image_evidences),
                "image_quality": "usable",
                "mime_type": primary.mime_type or "image/jpeg",
                "file_size_bytes": primary.file_size_bytes,
                "surface_damage_signal": surface_damage,
                "camera_metadata_present": bool(meta),
                "heuristic_source": heuristic_source,
            },
            "limitations": [
                "Rule-based heuristic inference; not a trained convolutional or vision model.",
                "Production vision requires weights trained on municipal datasets.",
            ],
        }
