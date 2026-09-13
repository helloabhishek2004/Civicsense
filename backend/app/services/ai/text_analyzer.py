import re
from typing import Any

from app.models.enums import SeverityLevel
from app.services.ai.text_interface import (
    TextInferenceOutcome,
    TextModel,
    TextModelMetadata,
    TextModelStatus,
    TextPrediction,
)

CANONICAL_TEXT_CATEGORIES: list[str] = [
    "Pothole",
    "Road Damage",
    "Garbage",
    "Water Leakage",
    "Streetlight",
    "Other",
]


def text_result_to_probabilities(text_res: dict[str, Any]) -> dict[str, float]:
    """Map text analyzer output into normalized canonical probability distribution."""
    raw_cat = text_res.get("predicted_category")
    if raw_cat == "Drainage":
        pred_cat = "Water Leakage"
    elif raw_cat in CANONICAL_TEXT_CATEGORIES:
        pred_cat = str(raw_cat)
    else:
        pred_cat = "Other"

    conf = float(text_res.get("confidence", 0.45))
    conf = min(0.95, max(0.10, conf))

    # Distribute residual probability mass evenly across other 5 categories
    rem = (1.0 - conf) / (len(CANONICAL_TEXT_CATEGORIES) - 1)
    probs = {c: round(rem, 4) for c in CANONICAL_TEXT_CATEGORIES}
    probs[pred_cat] = round(conf, 4)

    # Re-normalize to sum strictly to 1.0
    tot = sum(probs.values())
    if tot > 0:
        probs = {c: round(p / tot, 4) for c, p in probs.items()}
        diff = round(1.0 - sum(probs.values()), 4)
        probs["Other"] = round(probs["Other"] + diff, 4)
    return probs


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

        res: dict[str, Any] = {
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
        res["class_probabilities"] = text_result_to_probabilities(res)
        return res


class PrototypeTextModel(TextModel):
    """Adapter wrapping PrototypeTextPatternAnalyzer behind canonical TextModel interface."""

    def __init__(self) -> None:
        self._analyzer = PrototypeTextPatternAnalyzer()
        self._metadata = TextModelMetadata(
            model_name="prototype_text_pattern_analyzer",
            model_version="1.0.0",
            architecture_family="lexical_rules",
            num_classes=6,
            canonical_classes=list(CANONICAL_TEXT_CATEGORIES),
            device="cpu",
            runtime="prototype_rules",
        )

    def predict(self, text: str) -> TextPrediction:
        """Classify text using deterministic rule engine."""
        if not text or not text.strip():
            # Return uniform/default distribution for empty input
            uniform = {
                c: round(1.0 / len(CANONICAL_TEXT_CATEGORIES), 4) for c in CANONICAL_TEXT_CATEGORIES
            }
            diff = round(1.0 - sum(uniform.values()), 4)
            uniform["Other"] = round(uniform["Other"] + diff, 4)
            return TextPrediction(
                predicted_category="Other",
                confidence=0.1667,
                probabilities=uniform,
                status=TextInferenceOutcome.EMPTY_OR_INVALID_INPUT,
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_metadata={"reason": "empty_input"},
            )

        res = self._analyzer.analyze(text)
        probs = res["class_probabilities"]
        cat = str(res["predicted_category"])
        conf = float(probs.get(cat, res["confidence"]))

        status = TextInferenceOutcome.SUCCESS
        if conf < 0.40:
            status = TextInferenceOutcome.LOW_CONFIDENCE

        return TextPrediction(
            predicted_category=cat,
            confidence=conf,
            probabilities=probs,
            status=status,
            model_name=self._metadata.model_name,
            model_version=self._metadata.model_version,
            inference_metadata={
                "matched_terms": res.get("matched_terms", []),
                "urgency_signals": res.get("urgency_signals", []),
                "token_count": res.get("token_count", 0),
            },
        )

    def get_metadata(self) -> TextModelMetadata:
        """Return model metadata."""
        return self._metadata

    def get_status(self) -> TextModelStatus:
        """Return readiness status."""
        return TextModelStatus.READY
