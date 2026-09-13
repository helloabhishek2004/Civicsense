"""CivicSense AI Confidence Calibration & Uncertainty Quantification Module.

Mathematical Foundation:
-----------------------
1. Formal Logit Temperature Scaling (Guo et al., 2017):
   Given raw neural network logits z in R^K, formal temperature scaling computes:
       P_calib(y = c | x) = exp(z_c / T) / sum_j exp(z_j / T) = softmax(z / T)
   where T > 0 is a scalar parameter optimized on a validation set (e.g. via NLL).

2. Probability-Level Power-Law Transformation:
   In multimodal fusion, predictions combine a neural vision model with a deterministic
   rule/lexicon-based text analyzer (which does not produce neural logits). The fused
   probability vector P_raw = w_text * P_text + w_vision * P_vision is a convex combination
   of probability distributions.

   Applying temperature scaling at the probability level computes:
       P_calib(c) = P_raw(c)^(1 / T) / sum_j P_raw(j)^(1 / T)

   Mathematical properties of this transformation:
   - Monotonicity / Argmax Invariance: For any T > 0 and any categories a, b:
         P_raw(a) > P_raw(b) <=> P_calib(a) > P_calib(b)
     The top-1 category prediction is strictly invariant to T for all T > 0.
   - Uniform Distribution Invariance: If P_raw is uniform (1/K for all c),
     P_calib remains exactly uniform for all T > 0.
   - Limit T -> 0: P_calib approaches a one-hot distribution on argmax P_raw.
   - Limit T -> inf: P_calib approaches the uniform distribution (1/K).
   - Entropy Sharpening (T < 1): Concentrates probability mass toward the dominant class.
   - Entropy Softening (T > 1): Disperses probability mass, increasing uncertainty.

Implementation Note:
--------------------
In CivicSense, probability-level transformation is explicitly recognized as a post-fusion
power-law calibration heuristic, distinct from raw logit temperature scaling.
"""

from __future__ import annotations

import math
from typing import Any


def calculate_brier_score(
    y_true: list[str],
    probabilities_list: list[dict[str, float]],
    classes: list[str],
) -> float:
    """Calculate multi-class Brier score: mean squared error vs one-hot targets.

    Formula: Brier = (1 / N) * sum_{n=1}^N sum_{c=1}^K (P_{n, c} - Y_{n, c})^2
    Range: [0.0, 2.0], where 0.0 is perfect deterministic calibration.
    """
    if not y_true or len(y_true) != len(probabilities_list):
        return 0.0

    total_error = 0.0
    for gt, probs in zip(y_true, probabilities_list, strict=False):
        for c in classes:
            target = 1.0 if gt == c else 0.0
            pred_p = float(probs.get(c, 0.0))
            total_error += (pred_p - target) ** 2

    return round(total_error / len(y_true), 4)


def calculate_nll(
    y_true: list[str],
    probabilities_list: list[dict[str, float]],
    classes: list[str] | None = None,
    eps: float = 1e-12,
) -> float:
    """Calculate Negative Log-Likelihood (cross-entropy loss).

    Formula: NLL = - (1 / N) * sum_{n=1}^N log(max(eps, P_n(y_n)))
    Range: [0.0, inf), where lower is better.
    """
    if not y_true or len(y_true) != len(probabilities_list):
        return 0.0

    total_nll = 0.0
    for gt, probs in zip(y_true, probabilities_list, strict=False):
        p_target = float(probs.get(gt, 0.0))
        p_clamped = max(eps, min(1.0, p_target))
        total_nll -= math.log(p_clamped)

    return round(total_nll / len(y_true), 4)


def calculate_ece(
    y_true: list[str],
    y_pred: list[str],
    confidences: list[float],
    num_bins: int = 10,
) -> tuple[float, list[dict[str, Any]]]:
    """Calculate Expected Calibration Error (ECE) across confidence bins.

    Formula: ECE = sum_{b=1}^B (|B_b| / N) * |acc(B_b) - conf(B_b)|
    """
    if not y_true or len(y_true) != len(y_pred) or len(y_true) != len(confidences):
        return 0.0, []

    total_samples = len(y_true)
    bin_size = 1.0 / num_bins
    ece = 0.0
    bins_data: list[dict[str, Any]] = []

    for b in range(num_bins):
        bin_lower = b * bin_size
        bin_upper = (b + 1) * bin_size

        # Group samples falling into bin [lower, upper) (or [lower, upper] for final bin)
        indices = [
            i
            for i, conf in enumerate(confidences)
            if (bin_lower <= conf < bin_upper) or (b == num_bins - 1 and conf == 1.0)
        ]

        count = len(indices)
        if count > 0:
            bin_acc = sum(1 for i in indices if y_true[i] == y_pred[i]) / count
            bin_conf = sum(confidences[i] for i in indices) / count
            calibration_gap = abs(bin_acc - bin_conf)
            weight = count / total_samples
            ece += weight * calibration_gap

            bins_data.append(
                {
                    "bin_index": b,
                    "range": [round(bin_lower, 2), round(bin_upper, 2)],
                    "count": count,
                    "accuracy": round(bin_acc, 4),
                    "confidence": round(bin_conf, 4),
                    "gap": round(calibration_gap, 4),
                }
            )
        else:
            bins_data.append(
                {
                    "bin_index": b,
                    "range": [round(bin_lower, 2), round(bin_upper, 2)],
                    "count": 0,
                    "accuracy": None,
                    "confidence": None,
                    "gap": 0.0,
                }
            )

    return round(ece, 4), bins_data


def apply_temperature(
    probabilities: dict[str, float],
    temperature: float,
) -> dict[str, float]:
    """Apply probability-level temperature scaling: P(c)^(1/T) / sum_j P(j)^(1/T).

    Preserves top-1 rank (argmax) strictly for any temperature > 0.
    """
    if temperature <= 0.0:
        raise ValueError(f"Temperature must be strictly positive, got {temperature}")

    if abs(temperature - 1.0) < 1e-4:
        return dict(probabilities)

    # Check for non-positive or empty input
    if not probabilities or all(v <= 0.0 for v in probabilities.values()):
        k = len(probabilities) if probabilities else 1
        return {c: 1.0 / k for c in probabilities}

    inv_t = 1.0 / temperature
    # Use log-sum-exp trick on log(max(1e-12, p)) * inv_t
    log_p = {c: math.log(max(1e-12, p)) * inv_t for c, p in probabilities.items()}
    max_log = max(log_p.values())
    exp_p = {c: math.exp(v - max_log) for c, v in log_p.items()}
    sum_exp = sum(exp_p.values())
    if sum_exp <= 0.0:
        k = len(probabilities)
        return {c: 1.0 / k for c in probabilities}

    normalized = {c: exp_p[c] / sum_exp for c in exp_p}
    # Clean tiny numerical drift
    tot = sum(normalized.values())
    return {c: p / tot for c, p in normalized.items()}


def fit_temperature_scaling(
    raw_probabilities_list: list[dict[str, float]],
    y_true: list[str],
    classes: list[str],
    temp_range: tuple[float, float] = (0.5, 2.5),
    steps: int = 41,
    criterion: str = "brier",
) -> tuple[float, float, float]:
    """Grid search for optimal temperature T on a held-out tuning split.

    DO NOT fit temperature scaling on the frozen evaluation benchmark.

    Args:
        raw_probabilities_list: Tuning set raw uncalibrated probabilities.
        y_true: Ground-truth class labels.
        classes: Canonical category list.
        temp_range: (min_T, max_T) search interval.
        steps: Number of evaluation points in interval.
        criterion: 'brier' (Brier Score) or 'nll' (Negative Log-Likelihood).

    Returns:
        (best_T, uncalibrated_score, calibrated_score)
    """
    if criterion == "nll":
        uncalibrated_score = calculate_nll(y_true, raw_probabilities_list, classes)
    else:
        uncalibrated_score = calculate_brier_score(y_true, raw_probabilities_list, classes)

    best_t = 1.0
    best_score = uncalibrated_score

    t_min, t_max = temp_range
    step_size = (t_max - t_min) / (steps - 1) if steps > 1 else 0.0

    for i in range(steps):
        t = round(t_min + (i * step_size), 4)
        if t <= 0.0:
            continue
        scaled_probs = [apply_temperature(p, t) for p in raw_probabilities_list]
        if criterion == "nll":
            score = calculate_nll(y_true, scaled_probs, classes)
        else:
            score = calculate_brier_score(y_true, scaled_probs, classes)

        if score < best_score:
            best_score = score
            best_t = t

    return best_t, uncalibrated_score, best_score

