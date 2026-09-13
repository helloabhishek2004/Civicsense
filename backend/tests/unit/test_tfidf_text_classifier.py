"""CivicSense Phase 4A: Unit Tests for TF-IDF Text Classifier.

Validates:
1. Loading trained TF-IDF pipeline from disk
2. Schema conformity to TextModel base class
3. Predictions on valid civic issue text
4. Probability normalization across 6 canonical classes
5. Edge case handling (empty strings, out-of-vocabulary words)
"""

from pathlib import Path

from app.services.ai.text_interface import (
    CANONICAL_TEXT_CATEGORIES,
    TextInferenceOutcome,
    TextModel,
    TextModelStatus,
)
from app.services.ai.tfidf_text_classifier import TFIDFTextClassifier

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = REPO_ROOT / "models" / "tfidf_baseline" / "tfidf_classifier.pkl"


def test_tfidf_classifier_loading() -> None:
    """TFIDFTextClassifier loads correctly and reports READY status."""
    assert MODEL_PATH.exists(), f"TF-IDF model artifact {MODEL_PATH} must exist"
    model = TFIDFTextClassifier(model_path=MODEL_PATH)
    assert isinstance(model, TextModel)
    assert model.get_status() == TextModelStatus.READY
    assert model.get_metadata().architecture_family == "tfidf_linear"


def test_tfidf_classifier_predict_valid_text() -> None:
    """TFIDFTextClassifier classifies common defect texts correctly."""
    model = TFIDFTextClassifier(model_path=MODEL_PATH)
    pred = model.predict("water leak pipe leaking on road")

    assert pred.predicted_category == "Water Leakage"
    assert pred.status == TextInferenceOutcome.SUCCESS
    assert pred.confidence >= 0.35
    assert set(pred.probabilities.keys()) == set(CANONICAL_TEXT_CATEGORIES)
    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 1e-3


def test_tfidf_classifier_empty_input() -> None:
    """TFIDFTextClassifier gracefully handles empty/whitespace input."""
    model = TFIDFTextClassifier(model_path=MODEL_PATH)
    pred = model.predict("    ")

    assert pred.predicted_category == "Other"
    assert pred.status == TextInferenceOutcome.EMPTY_OR_INVALID_INPUT
    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 1e-3


def test_tfidf_classifier_unseen_vocabulary() -> None:
    """TFIDFTextClassifier handles completely foreign words without crashing."""
    model = TFIDFTextClassifier(model_path=MODEL_PATH)
    pred = model.predict("xylophone zephyr quantum quasar nebula")

    assert pred.predicted_category in CANONICAL_TEXT_CATEGORIES
    assert pred.status in (TextInferenceOutcome.SUCCESS, TextInferenceOutcome.LOW_CONFIDENCE)
    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 1e-3


def test_tfidf_classifier_missing_file() -> None:
    """Missing model file sets status to UNAVAILABLE."""
    non_existent = REPO_ROOT / "models" / "missing_tfidf.pkl"
    model = TFIDFTextClassifier(model_path=non_existent)
    assert model.get_status() == TextModelStatus.UNAVAILABLE
    pred = model.predict("Some valid text")
    assert pred.status == TextInferenceOutcome.MODEL_UNAVAILABLE
