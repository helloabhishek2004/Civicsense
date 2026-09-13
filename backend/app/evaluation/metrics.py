import math
from typing import Any


def calculate_latency_percentiles(latencies: list[float]) -> dict[str, Any]:
    """Calculate comprehensive latency percentiles and distribution statistics in milliseconds."""
    if not latencies:
        return {
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "stddev": 0.0,
            "cold_start_latency_ms": 0.0,
            "warm_mean_ms": 0.0,
            "sample_count": 0,
        }

    cold_start = latencies[0]
    warm_vals = latencies[1:] if len(latencies) > 1 else [latencies[0]]
    overall_mean = sum(latencies) / len(latencies)
    warm_mean = sum(warm_vals) / len(warm_vals)

    if len(latencies) > 1:
        variance = sum((x - overall_mean) ** 2 for x in latencies) / (len(latencies) - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0

    sorted_vals = sorted(latencies)
    n = len(sorted_vals)

    def _get_p(p: float) -> float:
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return round(float(sorted_vals[int(k)]), 2)
        d0 = sorted_vals[int(f)] * (c - k)
        d1 = sorted_vals[int(c)] * (k - f)
        return round(float(d0 + d1), 2)

    return {
        "p50": _get_p(0.50),
        "p90": _get_p(0.90),
        "p95": _get_p(0.95),
        "p99": _get_p(0.99),
        "min": round(float(sorted_vals[0]), 2),
        "max": round(float(sorted_vals[-1]), 2),
        "mean": round(float(overall_mean), 2),
        "stddev": round(float(stddev), 2),
        "cold_start_latency_ms": round(float(cold_start), 2),
        "warm_mean_ms": round(float(warm_mean), 2),
        "sample_count": n,
    }


def calculate_classification_metrics(
    y_true: list[str],
    y_pred: list[str],
    categories: list[str] | None = None,
    review_required_flags: list[bool] | None = None,
) -> dict[str, Any]:
    """Calculate comprehensive classification metrics using pure Python standard library.

    Supports:
    - Overall Accuracy
    - Macro Precision, Recall, F1
    - Per-class Precision, Recall, F1, Support
    - Balanced Accuracy
    - 2D Confusion Matrix with deterministic label ordering
    - Abstention / Human-Review Rate
    - Selective Accuracy (accuracy on accepted/unreviewed subset)
    """
    total = len(y_true)
    if total == 0 or len(y_pred) != total:
        return {
            "total_samples": 0,
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "balanced_accuracy": 0.0,
            "abstention_rate": 0.0,
            "selective_accuracy": 0.0,
            "per_class": {},
            "confusion_matrix": {"classes": categories or [], "matrix": []},
        }

    # Determine deterministic category order
    if categories is not None:
        cat_order = list(categories)
        for c in sorted(set(y_true) | set(y_pred)):
            if c not in cat_order:
                cat_order.append(c)
    else:
        cat_order = sorted(list(set(y_true) | set(y_pred)))

    cat_to_idx = {c: i for i, c in enumerate(cat_order)}
    num_cats = len(cat_order)

    # Initialize confusion matrix [true_idx][pred_idx]
    matrix = [[0 for _ in range(num_cats)] for _ in range(num_cats)]
    correct = 0

    for t, p in zip(y_true, y_pred, strict=True):
        if t == p:
            correct += 1
        t_idx = cat_to_idx.get(t)
        p_idx = cat_to_idx.get(p)
        if t_idx is not None and p_idx is not None:
            matrix[t_idx][p_idx] += 1

    accuracy = round(correct / total, 4)

    # Per-class metrics
    per_class: dict[str, dict[str, float | int]] = {}
    f1_list: list[float] = []
    prec_list: list[float] = []
    rec_list: list[float] = []

    for i, cat in enumerate(cat_order):
        tp = matrix[i][i]
        fp = sum(matrix[r][i] for r in range(num_cats)) - tp
        fn = sum(matrix[i][c] for c in range(num_cats)) - tp
        support = sum(matrix[i])

        prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = round(2 * (prec * rec) / (prec + rec), 4) if (prec + rec) > 0 else 0.0

        per_class[cat] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": support,
        }

        # Only compute macro average over classes that exist in ground truth
        if support > 0:
            f1_list.append(f1)
            prec_list.append(prec)
            rec_list.append(rec)

    macro_f1 = round(sum(f1_list) / len(f1_list), 4) if f1_list else 0.0
    macro_prec = round(sum(prec_list) / len(prec_list), 4) if prec_list else 0.0
    macro_rec = round(sum(rec_list) / len(rec_list), 4) if rec_list else 0.0
    balanced_acc = macro_rec

    # Abstention / Review Rate
    abstention_rate = 0.0
    selective_acc = 0.0
    if review_required_flags and len(review_required_flags) == total:
        abstained_count = sum(1 for r in review_required_flags if r)
        abstention_rate = round(abstained_count / total, 4)

        accepted_indices = [idx for idx, r in enumerate(review_required_flags) if not r]
        if accepted_indices:
            accepted_correct = sum(
                1 for idx in accepted_indices if y_true[idx] == y_pred[idx]
            )
            selective_acc = round(accepted_correct / len(accepted_indices), 4)

    return {
        "total_samples": total,
        "accuracy": accuracy,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "macro_f1": macro_f1,
        "balanced_accuracy": balanced_acc,
        "abstention_rate": abstention_rate,
        "selective_accuracy": selective_acc,
        "per_class": per_class,
        "confusion_matrix": {
            "classes": cat_order,
            "matrix": matrix,
        },
    }


def calculate_confidence_metrics(
    confidences: list[float],
    is_correct_flags: list[bool],
    confidence_tiers: list[str] | None = None,
    review_required_flags: list[bool] | None = None,
) -> dict[str, Any]:
    """Calculate confidence calibration, distribution, and bucketed accuracy metrics."""
    total = len(confidences)
    if total == 0:
        return {
            "mean_confidence": 0.0,
            "confidence_by_tier": {},
            "accuracy_by_tier": {},
            "confidence_buckets": [],
            "high_confidence_error_count": 0,
            "low_confidence_count": 0,
            "manual_review_count": 0,
            "manual_review_rate": 0.0,
        }

    mean_conf = round(sum(confidences) / total, 4)

    tiers = ["HIGH", "MEDIUM", "LOW", "UNCERTAIN", "FAILED"]
    tier_counts: dict[str, int] = {t: 0 for t in tiers}
    tier_correct: dict[str, int] = {t: 0 for t in tiers}
    if confidence_tiers and len(confidence_tiers) == total:
        for tier, correct in zip(confidence_tiers, is_correct_flags, strict=True):
            tier_str = str(tier).upper()
            if tier_str in tier_counts:
                tier_counts[tier_str] += 1
                if correct:
                    tier_correct[tier_str] += 1
            else:
                tier_counts[tier_str] = 1
                tier_correct[tier_str] = 1 if correct else 0

    accuracy_by_tier = {
        t: round(tier_correct[t] / tier_counts[t], 4) if tier_counts[t] > 0 else 0.0
        for t in tier_counts
        if tier_counts[t] > 0
    }

    bucket_defs = [
        ("[0.0, 0.50)", 0.0, 0.50),
        ("[0.50, 0.60)", 0.50, 0.60),
        ("[0.60, 0.70)", 0.60, 0.70),
        ("[0.70, 0.80)", 0.70, 0.80),
        ("[0.80, 0.90)", 0.80, 0.90),
        ("[0.90, 1.00]", 0.90, 1.01),
    ]
    bucket_results = []
    for label, low, high in bucket_defs:
        b_samples = [
            (c, corr)
            for c, corr in zip(confidences, is_correct_flags, strict=True)
            if low <= c < high or (high > 1.0 and c == 1.0)
        ]
        b_count = len(b_samples)
        b_corr = sum(1 for _, corr in b_samples if corr)
        b_acc = round(b_corr / b_count, 4) if b_count > 0 else 0.0
        bucket_results.append({
            "bucket": label,
            "sample_count": b_count,
            "correct_count": b_corr,
            "accuracy": b_acc,
        })

    high_conf_errors = sum(
        1
        for c, corr in zip(confidences, is_correct_flags, strict=True)
        if c >= 0.70 and not corr
    )
    low_conf_count = sum(1 for c in confidences if c < 0.60)

    review_count = 0
    if review_required_flags:
        review_count = sum(1 for r in review_required_flags if r)

    return {
        "mean_confidence": mean_conf,
        "confidence_by_tier": {k: v for k, v in tier_counts.items() if v > 0},
        "accuracy_by_tier": accuracy_by_tier,
        "confidence_buckets": bucket_results,
        "high_confidence_error_count": high_conf_errors,
        "low_confidence_count": low_conf_count,
        "manual_review_count": review_count,
        "manual_review_rate": round(review_count / total, 4) if total > 0 else 0.0,
    }


def classify_failure_type(
    ground_truth_category: str,
    predicted_category: str,
    text_description: str | None = None,
    is_blurry: bool = False,
    is_low_res: bool = False,
    evidence_agreement: float | None = None,
    pipeline_errors: list[str] | None = None,
) -> str:
    """Classify inference failure into heuristic diagnostic categories."""
    if pipeline_errors:
        return "PIPELINE_ERROR"

    if ground_truth_category == predicted_category:
        return "NONE"

    if predicted_category == "Other":
        if is_blurry or is_low_res:
            return "LOW_VISUAL_SIGNAL"
        if not text_description or len(text_description.strip()) < 10:
            return "INSUFFICIENT_CONTEXT"
        return "INSUFFICIENT_CONTEXT"

    if evidence_agreement is not None and evidence_agreement < 0.40:
        return "TEXT_VISION_CONFLICT"

    if is_blurry:
        return "LOW_VISUAL_SIGNAL"

    if text_description:
        text_lower = text_description.lower()
        if ground_truth_category.lower() not in text_lower:
            return "MISLEADING_TEXT"

    return "CATEGORY_CONFUSION"
