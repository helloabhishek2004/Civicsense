"""CivicSense Phase 4A: Unit Tests for Semantic Text Classifier.

Validates:
1. Strategy B (Trained Head) loading from offline artifact
2. Strategy A (Zero-Shot Prototypes) initialization and prediction
3. Valid inference producing normalized 6-class distributions
4. Empty/whitespace input handling
5. Graceful degradation when encoder is unavailable
"""

from pathlib import Path

from app.services.ai.semantic_text_classifier import SemanticTextClassifier
from app.services.ai.semantic_text_encoder import MiniLMTextEncoder
from app.services.ai.text_interface import (
    CANONICAL_TEXT_CATEGORIES,
    TextInferenceOutcome,
    TextModel,
    TextModelStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = REPO_ROOT / "models" / "all_minilm_l6_v2"
HEAD_PATH = MODEL_DIR / "minilm_classifier_head.pkl"


def test_semantic_classifier_trained_head_loading() -> None:
    """Classifier loads trained logistic head and reports READY status."""
    assert HEAD_PATH.exists(), f"Classification head {HEAD_PATH} must exist"
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    classifier = SemanticTextClassifier(
        encoder=encoder,
        head_path=HEAD_PATH,
        strategy="trained_head",
    )
    assert isinstance(classifier, TextModel)
    assert classifier.get_status() == TextModelStatus.READY
    assert classifier.get_metadata().architecture_family == "transformer_minilm"


def test_semantic_classifier_predict_trained_head() -> None:
    """Trained head accurately classifies water leakage and outputs normalized probs."""
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    classifier = SemanticTextClassifier(
        encoder=encoder,
        head_path=HEAD_PATH,
        strategy="trained_head",
    )
    pred = classifier.predict("Main pipeline burst leaking fresh clean water onto street")

    assert pred.predicted_category == "Water Leakage"
    assert pred.status == TextInferenceOutcome.SUCCESS
    assert pred.confidence >= 0.50
    assert set(pred.probabilities.keys()) == set(CANONICAL_TEXT_CATEGORIES)
    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 1e-3


def test_semantic_classifier_zero_shot_prototypes() -> None:
    """Zero-shot prototype strategy computes cosine similarity across anchor texts."""
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    classifier = SemanticTextClassifier(
        encoder=encoder,
        strategy="zero_shot_prototypes",
        temperature=0.10,
    )
    assert classifier.get_status() == TextModelStatus.READY
    pred = classifier.predict("Street lamp pole bulb is completely dark and broken at night")

    assert pred.predicted_category == "Streetlight"
    assert pred.status == TextInferenceOutcome.SUCCESS
    assert set(pred.probabilities.keys()) == set(CANONICAL_TEXT_CATEGORIES)
    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 1e-3


def test_semantic_classifier_empty_input() -> None:
    """Empty or whitespace text yields EMPTY_OR_INVALID_INPUT."""
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    classifier = SemanticTextClassifier(
        encoder=encoder,
        head_path=HEAD_PATH,
        strategy="trained_head",
    )
    pred = classifier.predict("   \t\n")

    assert pred.predicted_category == "Other"
    assert pred.status == TextInferenceOutcome.EMPTY_OR_INVALID_INPUT
    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 1e-3


def test_semantic_classifier_encoder_unavailable() -> None:
    """When encoder cannot load, classifier returns MODEL_UNAVAILABLE gracefully."""
    non_existent = REPO_ROOT / "models" / "does_not_exist"
    bad_encoder = MiniLMTextEncoder(model_dir=non_existent)
    classifier = SemanticTextClassifier(encoder=bad_encoder)

    pred = classifier.predict("Any problem description")
    assert pred.status == TextInferenceOutcome.MODEL_UNAVAILABLE
    assert pred.predicted_category == "Other"
