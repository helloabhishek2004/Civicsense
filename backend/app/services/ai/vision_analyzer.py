from typing import Any

from app.models.enums import SeverityLevel
from app.models.evidence import Evidence


class PrototypeVisionAnalyzer:
    """Deterministic prototype vision analyzer.

    DISCLAIMER: This is a clearly labeled rule-based feature extractor and metadata inspector,
    NOT a trained deep neural network. Used for demonstrable pipeline simulation.
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
        uri_lower = primary.storage_uri.lower()
        meta = primary.metadata_json or {}

        # Inspect storage uri & metadata for prototype demo triggers
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
            # Ambiguous or generic image trigger (useful for testing conflict/low confidence)
            category = "Other"
            severity = SeverityLevel.LOW
            confidence = 0.52
            surface_damage = "unclassified_surface_feature"

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
            },
            "limitations": [
                "Rule-based heuristic inference; not a trained convolutional or vision model.",
                "Production vision requires weights trained on municipal datasets.",
            ],
        }
