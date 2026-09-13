"""CivicSense Phase 4A: Unit Tests for Lexical-Semantic Ensemble Text Model.

Validates:
1. Linear probability pooling and alpha parameter bounds
2. Behavior under alpha=0.0 (pure semantic) and alpha=1.0 (pure deterministic)
3. Concordant and discordant predictions
4. Empty input handling
5. Graceful fallback when one sub-model fails
"""

from pathlib import Path

import pytest

from app.services.ai.ensemble_text_model import EnsembleTextModel
from app.services.ai.semantic_text_classifier import SemanticTextClassifier
from app.services.ai.semantic_text_encoder import MiniLMTextEncoder
from app.services.ai.text_analyzer import PrototypeTextModel
from app.services.ai.text_interface import (
    CANONICAL_TEXT_CATEGORIES,
    TextInferenceOutcome,
    TextModel,
    TextModelStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = REPO_ROOT / "models" / "all_minilm_l6_v2"
HEAD_PATH = MODEL_DIR / "minilm_classifier_head.pkl"


def test_ensemble_alpha_validation() -> None:
    """Alpha must be strictly within [0.0, 1.0]."""
    with pytest.raises(ValueError):
        EnsembleTextModel(alpha=-0.1)

    with pytest.raises(ValueError):
        EnsembleTextModel(alpha=1.1)

    ens = EnsembleTextModel(alpha=0.5)
    assert ens.alpha == 0.5
    assert isinstance(ens, TextModel)
    assert ens.get_status() == TextModelStatus.READY


def test_ensemble_pure_deterministic_alpha_1() -> None:
    """With alpha=1.0, ensemble probabilities follow deterministic model."""
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    sem = SemanticTextClassifier(encoder=encoder, head_path=HEAD_PATH, strategy="trained_head")
    det = PrototypeTextModel()

    ens = EnsembleTextModel(deterministic_model=det, semantic_model=sem, alpha=1.0)
    pred = ens.predict("Deep dangerous pothole on 4th main")

    assert pred.predicted_category == "Pothole"
    assert pred.status == TextInferenceOutcome.SUCCESS
    assert pred.inference_metadata["effective_alpha"] == 1.0


def test_ensemble_pure_semantic_alpha_0() -> None:
    """With alpha=0.0, ensemble probabilities follow semantic model."""
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    sem = SemanticTextClassifier(encoder=encoder, head_path=HEAD_PATH, strategy="trained_head")
    det = PrototypeTextModel()

    ens = EnsembleTextModel(deterministic_model=det, semantic_model=sem, alpha=0.0)
    pred = ens.predict("Broken streetlight lamp dark road")

    assert pred.predicted_category == "Streetlight"
    assert pred.status == TextInferenceOutcome.SUCCESS
    assert pred.inference_metadata["effective_alpha"] == 0.0


def test_ensemble_balanced_alpha_05() -> None:
    """With alpha=0.5, probabilities are linearly combined and normalized."""
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    sem = SemanticTextClassifier(encoder=encoder, head_path=HEAD_PATH, strategy="trained_head")
    det = PrototypeTextModel()

    ens = EnsembleTextModel(deterministic_model=det, semantic_model=sem, alpha=0.5)
    pred = ens.predict("Overflowing garbage trash bin")

    assert pred.predicted_category == "Garbage"
    assert pred.status == TextInferenceOutcome.SUCCESS
    assert set(pred.probabilities.keys()) == set(CANONICAL_TEXT_CATEGORIES)
    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 1e-3


def test_ensemble_empty_input() -> None:
    """Empty input returns EMPTY_OR_INVALID_INPUT."""
    ens = EnsembleTextModel(alpha=0.5)
    pred = ens.predict("   ")

    assert pred.predicted_category == "Other"
    assert pred.status == TextInferenceOutcome.EMPTY_OR_INVALID_INPUT
    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 1e-3


def test_ensemble_fallback_when_semantic_unavailable() -> None:
    """When semantic model is unavailable, effective alpha becomes 1.0."""
    non_existent = REPO_ROOT / "models" / "does_not_exist"
    bad_encoder = MiniLMTextEncoder(model_dir=non_existent)
    bad_sem = SemanticTextClassifier(encoder=bad_encoder)
    det = PrototypeTextModel()

    ens = EnsembleTextModel(deterministic_model=det, semantic_model=bad_sem, alpha=0.5)
    pred = ens.predict("Deep pothole in asphalt")

    assert pred.status == TextInferenceOutcome.SUCCESS
    assert pred.predicted_category == "Pothole"
    assert pred.inference_metadata["effective_alpha"] == 1.0
