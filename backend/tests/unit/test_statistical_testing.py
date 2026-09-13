"""Unit tests for Paired Statistical Testing and Resampling."""

from __future__ import annotations

import math

import pytest

from app.evaluation.statistical_testing import (
    calculate_clopper_pearson_interval,
    calculate_selective_confidence_bounds,
    calculate_wilson_score_interval,
    mcnemar_paired_test,
    paired_bootstrap_intervals,
)

CANONICAL = ["Pothole", "Road Damage", "Garbage", "Water Leakage", "Streetlight", "Other"]


def test_mcnemar_equal_predictions_zero_discordant():
    y_true = ["Pothole", "Garbage", "Other"]
    pred = ["Pothole", "Garbage", "Other"]
    res = mcnemar_paired_test(y_true, pred, pred)

    assert res.discordant_total == 0
    assert res.n10_text_correct_fusion_wrong == 0
    assert res.n01_text_wrong_fusion_correct == 0
    assert res.p_value == 1.0
    assert res.accuracy_difference_pp == 0.0
    assert "zero discordant" in res.mcnemar_method


def test_mcnemar_b_equals_c_symmetric_discordant():
    # 4 samples: 1 both correct, 1 text correct/fusion wrong (b=1), 1 text wrong/fusion correct (c=1), 1 both wrong
    y_true = ["A", "B", "C", "D"]
    p_text = ["A", "B", "X", "Y"]   # Text: A, B correct (2/4)
    p_fuse = ["A", "Z", "C", "Y"]   # Fuse: A, C correct (2/4)

    res = mcnemar_paired_test(y_true, p_text, p_fuse)
    assert res.n11_both_correct == 1
    assert res.n10_text_correct_fusion_wrong == 1
    assert res.n01_text_wrong_fusion_correct == 1
    assert res.n00_both_wrong == 1
    assert res.discordant_total == 2
    assert res.accuracy_difference_pp == 0.0
    assert res.p_value == 1.0  # Exact binomial under b=c=1 gives 1.0


def test_mcnemar_b_zero_c_positive():
    # Fusion improves on 2 samples, never regresses
    y_true = ["A", "B", "C"]
    p_text = ["A", "X", "Y"]   # Text: A correct (1/3)
    p_fuse = ["A", "B", "C"]   # Fuse: A, B, C correct (3/3)

    res = mcnemar_paired_test(y_true, p_text, p_fuse)
    assert res.n10_text_correct_fusion_wrong == 0
    assert res.n01_text_wrong_fusion_correct == 2
    assert res.discordant_total == 2
    assert math.isclose(res.accuracy_difference_pp, (2.0 / 3.0) * 100.0, abs_tol=1e-2)
    assert res.p_value == 0.5  # 2 * 0.5^2 = 0.50


def test_mcnemar_large_discordant_chi_square():
    # 60 discordant pairs: b=40, c=20 (total=60 > 25)
    # n11 = 20, n00 = 20
    y_true = ["A"] * 80
    # Text gets 40 + 20 = 60 correct
    p_text = ["A"] * 60 + ["B"] * 20
    # Fusion gets 20 (both) + 20 (c) = 40 correct
    p_fuse = ["A"] * 20 + ["B"] * 40 + ["A"] * 20

    res = mcnemar_paired_test(y_true, p_text, p_fuse, cc=True)
    assert res.discordant_total == 60
    assert res.n10_text_correct_fusion_wrong == 40
    assert res.n01_text_wrong_fusion_correct == 20
    assert "continuity_corrected" in res.mcnemar_method
    # (|40 - 20| - 1)^2 / 60 = 19^2 / 60 = 361 / 60 = 6.0167
    assert math.isclose(res.statistic, 6.0167, rel_tol=1e-3)
    assert res.p_value < 0.05
    assert res.is_statistically_significant is True


def test_mcnemar_mismatched_lengths_raise_error():
    with pytest.raises(ValueError, match="Mismatched input lengths"):
        mcnemar_paired_test(["A", "B"], ["A"], ["A", "B"])


def test_mcnemar_empty_inputs_raise_error():
    with pytest.raises(ValueError, match="cannot be empty"):
        mcnemar_paired_test([], [], [])


def test_paired_bootstrap_determinism_and_intervals():
    y_true = ["Pothole", "Road Damage", "Garbage", "Other"] * 10
    p_text = ["Pothole", "Road Damage", "Garbage", "Other"] * 8 + ["Other"] * 8
    p_fuse = ["Pothole", "Road Damage", "Garbage", "Other"] * 9 + ["Other"] * 4

    b1 = paired_bootstrap_intervals(y_true, p_text, p_fuse, CANONICAL, iterations=500, seed=42)
    b2 = paired_bootstrap_intervals(y_true, p_text, p_fuse, CANONICAL, iterations=500, seed=42)

    assert b1["metrics"]["accuracy_difference_pp"] == b2["metrics"]["accuracy_difference_pp"]
    assert b1["metrics"]["fusion_macro_f1"]["mean"] == b2["metrics"]["fusion_macro_f1"]["mean"]
    assert b1["metrics"]["accuracy_difference_pp"]["ci_95_low"] <= b1["metrics"]["accuracy_difference_pp"]["ci_95_high"]


def test_wilson_score_interval_bounds():
    low, high = calculate_wilson_score_interval(k=81, n=81, confidence=0.95)
    assert 0.0 <= low < 1.0
    assert math.isclose(high, 1.0, abs_tol=1e-4)

    low_zero, high_zero = calculate_wilson_score_interval(k=0, n=81, confidence=0.95)
    assert math.isclose(low_zero, 0.0, abs_tol=1e-4)
    assert 0.0 < high_zero <= 1.0


def test_clopper_pearson_exact_bound_for_zero_errors():
    # 81 correct out of 81 (0 errors)
    low, high = calculate_clopper_pearson_interval(k=81, n=81, confidence=0.95)
    # alpha = 0.05, low = 0.05^(1/81) approx 0.9637
    expected_low = round(0.05 ** (1.0 / 81.0), 4)
    assert math.isclose(low, expected_low, abs_tol=1e-4)
    assert high == 1.0


def test_selective_confidence_bounds_structure():
    bounds = calculate_selective_confidence_bounds(
        total_samples=300,
        auto_accepted_samples=81,
        correct_auto_accepted=81,
        confidence_level=0.95,
    )
    assert bounds["coverage"] == 0.27
    assert bounds["selective_accuracy"] == 1.0
    assert bounds["observed_false_dispatches"] == 0
    assert bounds["selective_accuracy_ci_95_clopper_pearson"][0] > 0.95
    assert "Zero false dispatches were observed" in bounds["mathematical_note"]
