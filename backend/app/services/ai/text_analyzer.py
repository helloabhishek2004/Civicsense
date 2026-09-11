import re
from typing import Any

from app.models.enums import SeverityLevel


class PrototypeTextPatternAnalyzer:
    """Deterministic lexical and keyword pattern analyzer for citizen problem descriptions.

    DISCLAIMER: This is a lexical pattern analyzer, NOT a trained transformer / BERT model.
    """

    ENGINE_NAME = "Prototype Text Pattern Analyzer"
    MODE = "demo"

    CATEGORY_KEYWORDS = {
        "Pothole": ["pothole", "crater", "tarmac", "asphalt hole", "manhole open", "pit", "cavity"],
        "Garbage": [
            "garbage",
            "trash",
            "waste",
            "dump",
            "debris",
            "litter",
            "rubbish",
            "refuse",
            "bin overflow",
        ],
        "Water Leakage": [
            "water",
            "leak",
            "pipe burst",
            "drainage overflow",
            "pipeline",
            "spill",
            "flood",
            "sewage",
        ],
        "Streetlight": [
            "streetlight",
            "light",
            "dark",
            "lamp",
            "pole",
            "bulb",
            "illumination",
            "not glowing",
        ],
        "Road Damage": [
            "road",
            "crack",
            "pavement",
            "broken",
            "cave-in",
            "collapse",
            "sinkhole",
            "uneven",
        ],
        "Drainage": ["drain", "clogged", "gutter", "blockage", "waterlogging", "stormwater"],
    }

    URGENCY_KEYWORDS = [
        "hazard",
        "hazardous",
        "danger",
        "dangerous",
        "emergency",
        "urgent",
        "accident",
        "collapse",
        "risk",
        "school",
        "hospital",
        "elderly",
        "two-wheeler",
        "fallen",
        "injury",
        "fatal",
    ]

    def analyze(self, text: str) -> dict[str, Any]:
        """Analyze citizen problem text."""
        normalized = text.lower()
        words = re.findall(r"\b\w+\b", normalized)

        # Match category keywords
        matched_categories: dict[str, list[str]] = {}
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            found = [kw for kw in keywords if kw in normalized]
            if found:
                matched_categories[cat] = found

        # Determine best category match
        if matched_categories:
            best_cat = max(matched_categories.keys(), key=lambda c: len(matched_categories[c]))
            matched_terms = matched_categories[best_cat]
            confidence = min(0.92, 0.65 + (len(matched_terms) * 0.08))
        else:
            best_cat = "Other"
            matched_terms = []
            confidence = 0.45

        # Check urgency
        matched_urgency = [term for term in self.URGENCY_KEYWORDS if term in normalized]

        if len(matched_urgency) >= 2 or any(
            u in ["emergency", "accident", "fatal", "collapse"] for u in matched_urgency
        ):
            predicted_severity = SeverityLevel.CRITICAL
        elif len(matched_urgency) == 1:
            predicted_severity = SeverityLevel.HIGH
        elif best_cat in ["Pothole", "Water Leakage", "Road Damage"]:
            predicted_severity = SeverityLevel.MEDIUM
        else:
            predicted_severity = SeverityLevel.LOW

        return {
            "engine": self.ENGINE_NAME,
            "mode": self.MODE,
            "predicted_category": best_cat,
            "predicted_severity": predicted_severity,
            "confidence": round(confidence, 2),
            "matched_terms": matched_terms,
            "urgency_signals": matched_urgency,
            "token_count": len(words),
            "char_count": len(text),
            "limitations": [
                "Lexical pattern matching; no contextual embeddings or deep learning.",
            ],
        }
