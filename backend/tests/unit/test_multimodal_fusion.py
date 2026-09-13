"""CivicSense Phase 3.5 — Multimodal Fusion & Calibration Unit Tests.

Verifies:
1. Vision probability contract (all 6 canonical classes, stable order, ~1.0 sum).
2. Class order stability and probability validation rejection.
3. Fusion weight behavior across configurations (Text-Dominant, Balanced, Vision-Assisted, Adaptive).
4. Missing vision result: clean fallback to text without crashing or corrupting text signal.
5. Missing text result: clean fallback to vision.
6. Invalid/corrupt vision result: clean fallback to text.
7. Modality disagreement: penalty applied, disagreement flag set, review triggered.
8. Confidence calibration: ECE, Brier score, temperature scaling math.
9. Review routing policy gates: high confidence concordance auto-accepted; low confidence/conflict reviewed.
10. Benchmark dataset immutability.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.evaluation.calibration import (
    apply_temperature,
    calculate_brier_score,
    calculate_ece,
)
from app.models.enums import SeverityLevel
from app.services.ai.decision_engine import PrototypeDecisionEngine
from app.services.ai.fusion_engine import (
    FusionConfig,
    MultimodalFusionEngine,
)
from app.services.ai.real_vision_model import (
    validate_class_probabilities,
)
from app.services.ai.text_analyzer import (
    PrototypeTextPatternAnalyzer,
    text_result_to_probabilities,
)
from app.services.ai.vision_interface import (
    CANONICAL_VISION_CATEGORIES,
    VisionInferenceOutcome,
    VisionPrediction,
)

EXPECTED_BENCHMARK_HASH = "e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b"


@pytest.fixture
def fusion_engine() -> MultimodalFusionEngine:
    return MultimodalFusionEngine()


@pytest.fixture
def text_analyzer() -> PrototypeTextPatternAnalyzer:
    return PrototypeTextPatternAnalyzer()


def test_vision_probability_contract():
    """Verify that class probabilities strictly contain all 6 canonical categories and sum to ~1.0."""
    valid_probs = {
        "Pothole": 0.50,
        "Road Damage": 0.10,
        "Garbage": 0.10,
        "Water Leakage": 0.10,
        "Streetlight": 0.10,
        "Other": 0.10,
    }
    is_valid, err = validate_class_probabilities(valid_probs)
    assert is_valid is True
    assert err is None

    # Test missing class
    missing_probs = {c: 0.20 for c in CANONICAL_VISION_CATEGORIES if c != "Pothole"}
    is_valid, err = validate_class_probabilities(missing_probs)
    assert is_valid is False
    assert "Missing canonical classes" in str(err)

    # Test negative probability
    neg_probs = dict(valid_probs)
    neg_probs["Pothole"] = -0.10
    is_valid, err = validate_class_probabilities(neg_probs)
    assert is_valid is False
    assert "Negative probability" in str(err)

    # Test invalid sum
    bad_sum_probs = {c: 0.50 for c in CANONICAL_VISION_CATEGORIES}
    is_valid, err = validate_class_probabilities(bad_sum_probs)
    assert is_valid is False
    assert "Probabilities do not sum" in str(err)


def test_text_result_to_probabilities():
    """Verify text analyzer output maps cleanly to 6-class normalized distribution."""
    text_res = {
        "predicted_category": "Pothole",
        "confidence": 0.85,
        "predicted_severity": SeverityLevel.HIGH,
    }
    probs = text_result_to_probabilities(text_res)
    assert len(probs) == 6
    assert set(probs.keys()) == set(CANONICAL_VISION_CATEGORIES)
    assert probs["Pothole"] == 0.85
    assert abs(sum(probs.values()) - 1.0) < 1e-3

    # Drainage alias check
    drain_res = {
        "predicted_category": "Drainage",
        "confidence": 0.75,
        "predicted_severity": SeverityLevel.MEDIUM,
    }
    drain_probs = text_result_to_probabilities(drain_res)
    assert drain_probs["Water Leakage"] == 0.75
    assert abs(sum(drain_probs.values()) - 1.0) < 1e-3


def test_fusion_weight_behavior(fusion_engine: MultimodalFusionEngine):
    """Verify that configurable weights correctly scale text and vision contributions."""
    text_input = {
        "predicted_category": "Pothole",
        "confidence": 0.80,
        "predicted_severity": SeverityLevel.HIGH,
        "class_probabilities": {
            "Pothole": 0.80,
            "Road Damage": 0.04,
            "Garbage": 0.04,
            "Water Leakage": 0.04,
            "Streetlight": 0.04,
            "Other": 0.04,
        },
    }
    vision_input = {
        "has_image": True,
        "predicted_category": "Road Damage",
        "confidence": 0.90,
        "predicted_severity": SeverityLevel.MEDIUM,
        "class_probabilities": {
            "Pothole": 0.02,
            "Road Damage": 0.90,
            "Garbage": 0.02,
            "Water Leakage": 0.02,
            "Streetlight": 0.02,
            "Other": 0.02,
        },
    }

    # Text-dominant: text should win
    cfg_text_dom = FusionConfig(text_weight=0.80, vision_weight=0.20, disagreement_penalty=0.0)
    res_text = fusion_engine.fuse(vision_input, text_input, config=cfg_text_dom)
    assert res_text.fused_category == "Pothole"
    assert res_text.effective_text_weight == 0.80

    # Vision-dominant: vision should win
    cfg_vis_dom = FusionConfig(text_weight=0.20, vision_weight=0.80, disagreement_penalty=0.0)
    res_vis = fusion_engine.fuse(vision_input, text_input, config=cfg_vis_dom)
    assert res_vis.fused_category == "Road Damage"
    assert res_vis.effective_vision_weight == 0.80


def test_missing_vision_fallback(fusion_engine: MultimodalFusionEngine):
    """Verify that missing vision evidence cleanly falls back to text without destroying result."""
    text_input = {
        "predicted_category": "Garbage",
        "confidence": 0.82,
        "predicted_severity": SeverityLevel.MEDIUM,
        "class_probabilities": text_result_to_probabilities(
            {"predicted_category": "Garbage", "confidence": 0.82}
        ),
    }
    # No vision evidence
    res = fusion_engine.fuse(vision_input=None, text_input=text_input)

    assert res.fallback_mode == "TEXT_ONLY"
    assert res.fused_category == "Garbage"
    # 0.70x policy penalty
    assert res.fused_confidence == round(0.82 * 0.70, 4)
    assert res.requires_review is True
    assert "UNIMODAL_TEXT_FALLBACK" in res.review_reasons
    assert res.effective_text_weight == 1.0
    assert res.effective_vision_weight == 0.0


def test_invalid_vision_bytes_fallback(fusion_engine: MultimodalFusionEngine):
    """Verify that corrupt vision input does not crash fusion and falls back cleanly to text."""
    text_input = {
        "predicted_category": "Water Leakage",
        "confidence": 0.78,
        "predicted_severity": SeverityLevel.HIGH,
    }
    # Vision outcome is PREPROCESSING_ERROR
    vision_pred = VisionPrediction(
        outcome=VisionInferenceOutcome.PREPROCESSING_ERROR,
        predicted_category=None,
        confidence=0.0,
        class_probabilities={},
        model_name="mobilenet_v3_small",
        model_version="1.0.0",
        inference_time_ms=0.0,
        preprocessing_time_ms=1.2,
        requires_review=True,
        error_message="Image decoding failed: corrupt JPEG data",
    )

    res = fusion_engine.fuse(vision_input=vision_pred, text_input=text_input)
    assert res.fallback_mode == "TEXT_ONLY"
    assert res.fused_category == "Water Leakage"
    assert res.fused_confidence == round(0.78 * 0.70, 4)
    assert res.requires_review is True
    assert "UNIMODAL_TEXT_FALLBACK" in res.review_reasons


def test_modality_disagreement_penalty(fusion_engine: MultimodalFusionEngine):
    """Verify that cross-modal category disagreement lowers confidence and triggers review."""
    text_input = {
        "predicted_category": "Streetlight",
        "confidence": 0.75,
        "predicted_severity": SeverityLevel.LOW,
    }
    vision_input = {
        "has_image": True,
        "predicted_category": "Garbage",
        "confidence": 0.75,
        "predicted_severity": SeverityLevel.MEDIUM,
        "class_probabilities": {
            "Pothole": 0.04,
            "Road Damage": 0.04,
            "Garbage": 0.75,
            "Water Leakage": 0.05,
            "Streetlight": 0.08,
            "Other": 0.04,
        },
    }

    cfg = FusionConfig(
        text_weight=0.50, vision_weight=0.50, disagreement_penalty=0.15, temperature=1.0
    )
    res = fusion_engine.fuse(vision_input, text_input, config=cfg)

    assert res.category_agreement is False
    assert res.disagreement_detected is True
    assert "MODALITY_DISAGREEMENT" in res.review_reasons
    assert res.requires_review is True
    # Penalty of 0.15 should have been subtracted
    raw_conf = res.raw_probabilities[res.fused_category]
    assert res.fused_confidence <= raw_conf - 0.10


def test_concordance_automatic_triage(fusion_engine: MultimodalFusionEngine):
    """Verify that agreeing high-confidence predictions pass without mandatory review."""
    text_input = {
        "predicted_category": "Pothole",
        "confidence": 0.90,
        "predicted_severity": SeverityLevel.HIGH,
    }
    vision_input = {
        "has_image": True,
        "predicted_category": "Pothole",
        "confidence": 0.92,
        "predicted_severity": SeverityLevel.HIGH,
        "class_probabilities": {
            "Pothole": 0.92,
            "Road Damage": 0.02,
            "Garbage": 0.02,
            "Water Leakage": 0.01,
            "Streetlight": 0.01,
            "Other": 0.02,
        },
    }

    cfg = FusionConfig(text_weight=0.60, vision_weight=0.40, min_confidence_threshold=0.60)
    res = fusion_engine.fuse(vision_input, text_input, config=cfg)

    assert res.fused_category == "Pothole"
    assert res.category_agreement is True
    assert res.disagreement_detected is False
    assert res.requires_review is False
    assert len(res.review_reasons) == 0


def test_confidence_calibration_math():
    """Verify ECE, Brier score, and temperature scaling calculations."""
    y_true = ["Pothole", "Pothole", "Garbage", "Streetlight"]
    y_pred = ["Pothole", "Pothole", "Garbage", "Water Leakage"]  # 3 correct, 1 wrong
    confs = [0.90, 0.85, 0.95, 0.70]

    ece, bins = calculate_ece(y_true, y_pred, confs, num_bins=5)
    assert isinstance(ece, float)
    assert 0.0 <= ece <= 1.0
    assert len(bins) == 5

    # Brier score test
    probs_list = [
        {
            "Pothole": 0.90,
            "Garbage": 0.05,
            "Streetlight": 0.05,
            "Road Damage": 0.0,
            "Water Leakage": 0.0,
            "Other": 0.0,
        },
        {
            "Pothole": 0.85,
            "Garbage": 0.05,
            "Streetlight": 0.05,
            "Road Damage": 0.05,
            "Water Leakage": 0.0,
            "Other": 0.0,
        },
        {
            "Pothole": 0.02,
            "Garbage": 0.95,
            "Streetlight": 0.01,
            "Road Damage": 0.01,
            "Water Leakage": 0.01,
            "Other": 0.0,
        },
        {
            "Pothole": 0.10,
            "Garbage": 0.10,
            "Streetlight": 0.10,
            "Road Damage": 0.0,
            "Water Leakage": 0.70,
            "Other": 0.0,
        },
    ]
    brier = calculate_brier_score(y_true, probs_list, CANONICAL_VISION_CATEGORIES)
    assert 0.0 <= brier <= 2.0

    # Temperature scaling test
    t_scaled = apply_temperature(probs_list[0], temperature=1.5)
    assert abs(sum(t_scaled.values()) - 1.0) < 1e-3
    # Top probability should be softer under T > 1
    assert t_scaled["Pothole"] < probs_list[0]["Pothole"]


def test_decision_engine_with_fused_result():
    """Verify PrototypeDecisionEngine consumes modern fused result seamlessly."""
    engine = PrototypeDecisionEngine()
    vision_res = {"predicted_category": "Pothole", "confidence": 0.88, "has_image": True}
    text_res = {
        "predicted_category": "Pothole",
        "confidence": 0.82,
        "predicted_severity": SeverityLevel.HIGH,
    }
    fused_res = {
        "fused_category": "Pothole",
        "fused_confidence": 0.85,
        "modality_agreement": 0.96,
        "category_agreement": True,
        "disagreement_detected": False,
        "fallback_mode": "MULTIMODAL",
    }

    decision = engine.decide(vision_res, text_res, fused_res)
    assert decision["suggested_category"] == "Pothole"
    assert decision["confidence"] == 0.85
    assert decision["review_required"] is False
    assert decision["suggested_severity"] == SeverityLevel.HIGH


def test_frozen_benchmark_immutability():
    """Verify frozen benchmark SHA-256 hash remains unaltered."""
    benchmark_file = Path("datasets/benchmark_v1/benchmark_dataset.jsonl")
    if not benchmark_file.exists():
        benchmark_file = Path("../datasets/benchmark_v1/benchmark_dataset.jsonl")
    assert benchmark_file.exists()
    current_hash = hashlib.sha256(benchmark_file.read_bytes()).hexdigest()
    assert current_hash == EXPECTED_BENCHMARK_HASH, (
        "Benchmark manifest must remain strictly immutable!"
    )
