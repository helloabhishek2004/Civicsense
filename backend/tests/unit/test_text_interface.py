"""CivicSense Phase 4A — Text Model Interface Unit Tests.

Validates:
1. Canonical 6-class taxonomy for text intelligence
2. TextModelStatus, TextInferenceOutcome enums
3. TextModelMetadata and TextPrediction immutability and schema validation
4. PrototypeTextModel compliance with TextModel abstract base class
5. Error handling for empty / whitespace inputs
"""

import pytest
from pydantic import ValidationError

from app.services.ai.text_analyzer import PrototypeTextModel, PrototypeTextPatternAnalyzer
from app.services.ai.text_interface import (
    CANONICAL_TEXT_CATEGORIES,
    TextInferenceOutcome,
    TextModel,
    TextModelMetadata,
    TextModelStatus,
    TextPrediction,
)


def test_canonical_text_categories() -> None:
    """Validate 6 canonical civic issue categories."""
    assert len(CANONICAL_TEXT_CATEGORIES) == 6
    assert CANONICAL_TEXT_CATEGORIES == [
        "Pothole",
        "Road Damage",
        "Garbage",
        "Water Leakage",
        "Streetlight",
        "Other",
    ]


def test_text_model_metadata_immutability() -> None:
    """Metadata must be frozen/immutable."""
    meta = TextModelMetadata(
        model_name="test_model",
        model_version="1.0.0",
        architecture_family="transformer",
        num_classes=6,
        canonical_classes=list(CANONICAL_TEXT_CATEGORIES),
        device="cpu",
        runtime="pytorch_cpu",
    )
    assert meta.model_name == "test_model"
    assert meta.num_classes == 6
    with pytest.raises(ValidationError):
        meta.model_name = "new_model"  # type: ignore


def test_text_prediction_schema_and_immutability() -> None:
    """TextPrediction schema validation and frozen state."""
    pred = TextPrediction(
        predicted_category="Pothole",
        confidence=0.88,
        probabilities={c: 0.88 if c == "Pothole" else 0.024 for c in CANONICAL_TEXT_CATEGORIES},
        status=TextInferenceOutcome.SUCCESS,
        model_name="test_model",
        model_version="1.0.0",
        inference_metadata={"tokens": 12},
    )
    assert pred.predicted_category == "Pothole"
    assert pred.confidence == 0.88
    assert pred.status == TextInferenceOutcome.SUCCESS
    assert pred.probabilities["Pothole"] == 0.88
    with pytest.raises(ValidationError):
        pred.confidence = 0.50  # type: ignore


def test_prototype_text_model_conforms_to_text_model() -> None:
    """PrototypeTextModel must implement TextModel."""
    model = PrototypeTextModel()
    assert isinstance(model, TextModel)
    assert model.get_status() == TextModelStatus.READY
    meta = model.get_metadata()
    assert meta.model_name == "prototype_text_pattern_analyzer"
    assert meta.architecture_family == "lexical_rules"


def test_prototype_text_model_prediction() -> None:
    """PrototypeTextModel predicts categories from keywords."""
    model = PrototypeTextModel()
    pred = model.predict("Deep dangerous pothole on 4th cross road")
    assert pred.predicted_category == "Pothole"
    assert pred.confidence > 0.50
    assert pred.status == TextInferenceOutcome.SUCCESS
    assert set(pred.probabilities.keys()) == set(CANONICAL_TEXT_CATEGORIES)
    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 0.02


def test_prototype_text_model_empty_input() -> None:
    """PrototypeTextModel returns EMPTY_OR_INVALID_INPUT for blank text."""
    model = PrototypeTextModel()
    pred = model.predict("   ")
    assert pred.predicted_category == "Other"
    assert pred.status == TextInferenceOutcome.EMPTY_OR_INVALID_INPUT
    assert set(pred.probabilities.keys()) == set(CANONICAL_TEXT_CATEGORIES)
    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 0.02


def test_deterministic_text_analyzer_invariants() -> None:
    """PrototypeTextPatternAnalyzer must remain functional and unchanged."""
    analyzer = PrototypeTextPatternAnalyzer()
    res = analyzer.analyze("Huge pile of overflowing waste and garbage near bin")
    assert res["predicted_category"] == "Garbage"
    assert res["confidence"] >= 0.65
    assert "class_probabilities" in res
    assert len(res["class_probabilities"]) == 6
