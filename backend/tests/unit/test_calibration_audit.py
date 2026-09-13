"""Unit tests for Calibration Audit and Mathematical Properties."""

from __future__ import annotations

import math

import pytest

from app.evaluation.calibration import (
    apply_temperature,
    calculate_brier_score,
    calculate_nll,
    fit_temperature_scaling,
)

CANONICAL = ["Pothole", "Road Damage", "Garbage", "Water Leakage", "Streetlight", "Other"]


def test_uniform_distribution_invariance():
    uniform = {c: 1.0 / 6.0 for c in CANONICAL}
    for t in [0.2, 0.5, 1.0, 1.5, 2.0, 10.0]:
        scaled = apply_temperature(uniform, t)
        for c in CANONICAL:
            assert math.isclose(scaled[c], 1.0 / 6.0, rel_tol=1e-5), f"Failed at T={t}"


def test_argmax_preservation_for_various_temperatures():
    probs = {"Pothole": 0.45, "Road Damage": 0.25, "Garbage": 0.10, "Water Leakage": 0.10, "Streetlight": 0.05, "Other": 0.05}
    expected_best = "Pothole"
    for t in [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 3.0, 10.0]:
        scaled = apply_temperature(probs, t)
        best = max(scaled.keys(), key=lambda c: scaled[c])
        assert best == expected_best, f"Argmax changed at T={t}: {best} != {expected_best}"
        assert math.isclose(sum(scaled.values()), 1.0, rel_tol=1e-6)


def test_temperature_approaching_zero_becomes_one_hot():
    probs = {"Pothole": 0.45, "Road Damage": 0.25, "Garbage": 0.10, "Water Leakage": 0.10, "Streetlight": 0.05, "Other": 0.05}
    scaled = apply_temperature(probs, temperature=0.01)
    assert scaled["Pothole"] > 0.9999
    for c in CANONICAL:
        if c != "Pothole":
            assert scaled[c] < 1e-3


def test_temperature_approaching_infinity_becomes_uniform():
    probs = {"Pothole": 0.60, "Road Damage": 0.20, "Garbage": 0.10, "Water Leakage": 0.05, "Streetlight": 0.03, "Other": 0.02}
    scaled = apply_temperature(probs, temperature=100.0)
    for c in CANONICAL:
        assert math.isclose(scaled[c], 1.0 / 6.0, abs_tol=0.02)


def test_strictly_positive_temperature_enforced():
    probs = {c: 1.0 / 6.0 for c in CANONICAL}
    with pytest.raises(ValueError, match="strictly positive"):
        apply_temperature(probs, temperature=0.0)
    with pytest.raises(ValueError, match="strictly positive"):
        apply_temperature(probs, temperature=-0.5)


def test_probabilities_sum_to_one_and_no_nans():
    probs = {"Pothole": 0.999, "Road Damage": 0.001, "Garbage": 0.0, "Water Leakage": 0.0, "Streetlight": 0.0, "Other": 0.0}
    scaled = apply_temperature(probs, 0.5)
    assert not any(math.isnan(v) or math.isinf(v) for v in scaled.values())
    assert math.isclose(sum(scaled.values()), 1.0, rel_tol=1e-6)


def test_calculate_nll_correctness():
    y_true = ["Pothole", "Garbage"]
    perfect = [
        {c: 1.0 if c == "Pothole" else 0.0 for c in CANONICAL},
        {c: 1.0 if c == "Garbage" else 0.0 for c in CANONICAL},
    ]
    nll_perf = calculate_nll(y_true, perfect, CANONICAL)
    assert math.isclose(nll_perf, 0.0, abs_tol=1e-4)

    imperfect = [
        {"Pothole": 0.5, "Road Damage": 0.5, "Garbage": 0.0, "Water Leakage": 0.0, "Streetlight": 0.0, "Other": 0.0},
        {"Pothole": 0.0, "Road Damage": 0.0, "Garbage": 0.5, "Water Leakage": 0.5, "Streetlight": 0.0, "Other": 0.0},
    ]
    nll_imp = calculate_nll(y_true, imperfect, CANONICAL)
    assert math.isclose(nll_imp, 0.6931, abs_tol=1e-3)


def test_calculate_brier_score_correctness():
    y_true = ["Pothole"]
    perfect = [{c: 1.0 if c == "Pothole" else 0.0 for c in CANONICAL}]
    brier_perf = calculate_brier_score(y_true, perfect, CANONICAL)
    assert brier_perf == 0.0

    worst = [{c: 1.0 if c == "Garbage" else 0.0 for c in CANONICAL}]
    brier_worst = calculate_brier_score(y_true, worst, CANONICAL)
    assert brier_worst == 2.0


def test_fit_temperature_scaling_optimization():
    y_true = ["Pothole", "Pothole"]
    overconfident = [
        {"Pothole": 0.95, "Road Damage": 0.05, "Garbage": 0.0, "Water Leakage": 0.0, "Streetlight": 0.0, "Other": 0.0},
        {"Pothole": 0.95, "Road Damage": 0.05, "Garbage": 0.0, "Water Leakage": 0.0, "Streetlight": 0.0, "Other": 0.0},
    ]
    best_t, uncal, cal = fit_temperature_scaling(overconfident, y_true, CANONICAL, temp_range=(0.5, 2.0), steps=5)
    assert best_t > 0.0
    assert cal <= uncal
