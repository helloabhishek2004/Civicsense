"""CivicSense Phase 3.5 — Multimodal Vision Integration, Fusion, Calibration & Evaluation.

Executes controlled, reproducible evaluation comparing:
A. Text-only classifier
B. Vision-only RealVisionModel (MobileNetV3-Small Exp B)
C. Multimodal Fused classifier across candidate configurations

Protocol:
1. Validates pre-evaluation frozen benchmark SHA-256 hash.
2. Evaluates candidate fusion configurations on curated validation set (n=119).
3. Fits confidence calibration (Temperature Scaling) on validation set.
4. Selects optimal fusion configuration based on validation metrics.
5. Evaluates selected configuration ONCE on frozen benchmark (n=300).
6. Conducts structured error analysis and failure breakdown.
7. Re-verifies post-evaluation frozen benchmark SHA-256 hash.
8. Exports complete JSON telemetry to datasets/evaluation_runs/multimodal_fusion_pilot/.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

# Ensure repo root and backend are on sys.path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.evaluation.calibration import (
    calculate_brier_score,
    calculate_ece,
    fit_temperature_scaling,
)
from app.services.ai.fusion_engine import (
    FusionConfig,
    MultimodalFusionEngine,
)
from app.services.ai.real_vision_model import RealVisionModel
from app.services.ai.text_analyzer import (
    PrototypeTextPatternAnalyzer,
    text_result_to_probabilities,
)
from app.services.ai.vision_interface import CANONICAL_VISION_CATEGORIES

EXPECTED_BENCHMARK_HASH = (
    "e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b"
)


def verify_benchmark_hash(benchmark_path: Path) -> str:
    """Verify and return SHA-256 hash of benchmark dataset."""
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_path}")
    h = hashlib.sha256(benchmark_path.read_bytes()).hexdigest()
    if h != EXPECTED_BENCHMARK_HASH:
        raise ValueError(
            f"Benchmark hash mismatch! Expected {EXPECTED_BENCHMARK_HASH}, got {h}"
        )
    return h


def compute_metrics(
    y_true: list[str],
    y_pred: list[str],
    probs_list: list[dict[str, float]],
    confs: list[float],
    classes: list[str],
) -> dict[str, Any]:
    """Compute standard classification, calibration, and per-class metrics."""
    total = len(y_true)
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = round(correct / total, 4) if total > 0 else 0.0

    per_class: dict[str, dict[str, Any]] = {}
    f1_list: list[float] = []
    prec_list: list[float] = []
    rec_list: list[float] = []

    for c in classes:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp == c)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != c and yp == c)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp != c)
        support = sum(1 for yt in y_true if yt == c)

        prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = round((2 * prec * rec) / (prec + rec), 4) if (prec + rec) > 0 else 0.0

        per_class[c] = {
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
        f1_list.append(f1)
        prec_list.append(prec)
        rec_list.append(rec)

    macro_f1 = round(sum(f1_list) / len(f1_list), 4)
    macro_prec = round(sum(prec_list) / len(prec_list), 4)
    macro_rec = round(sum(rec_list) / len(rec_list), 4)

    # Confusion Matrix
    matrix = [[0] * len(classes) for _ in range(len(classes))]
    c_to_idx = {c: idx for idx, c in enumerate(classes)}
    for yt, yp in zip(y_true, y_pred):
        if yt in c_to_idx and yp in c_to_idx:
            matrix[c_to_idx[yt]][c_to_idx[yp]] += 1

    # Calibration Metrics
    brier = calculate_brier_score(y_true, probs_list, classes)
    ece, bins_data = calculate_ece(y_true, y_pred, confs, num_bins=10)

    # Confidence Statistics
    mean_conf_overall = round(sum(confs) / total, 4) if total > 0 else 0.0
    correct_confs = [c for c, yt, yp in zip(confs, y_true, y_pred) if yt == yp]
    incorrect_confs = [c for c, yt, yp in zip(confs, y_true, y_pred) if yt != yp]
    mean_conf_correct = (
        round(sum(correct_confs) / len(correct_confs), 4) if correct_confs else 0.0
    )
    mean_conf_incorrect = (
        round(sum(incorrect_confs) / len(incorrect_confs), 4)
        if incorrect_confs
        else 0.0
    )

    return {
        "total_samples": total,
        "correct_samples": correct,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "brier_score": brier,
        "ece": ece,
        "confidence_stats": {
            "mean_confidence_overall": mean_conf_overall,
            "mean_confidence_correct": mean_conf_correct,
            "mean_confidence_incorrect": mean_conf_incorrect,
        },
        "per_class": per_class,
        "confusion_matrix": {
            "classes": classes,
            "matrix": matrix,
        },
        "calibration_bins": bins_data,
    }


def main() -> None:
    print("=" * 70)
    print("CivicSense Phase 3.5 — Multimodal Fusion & Calibration Evaluation")
    print("=" * 70)

    # Step 1: Verify Pre-Evaluation Benchmark Hash
    benchmark_file = repo_root / "datasets/benchmark_v1/benchmark_dataset.jsonl"
    pre_hash = verify_benchmark_hash(benchmark_file)
    print(f"Pre-Evaluation Benchmark Hash: {pre_hash} [VALID]")

    # Setup Models
    ckpt_path = repo_root / "models/mobilenet_v3_small_v1/exp_b/exp_b_best.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at: {ckpt_path}")

    vision_model = RealVisionModel(checkpoint_path=ckpt_path)
    text_analyzer = PrototypeTextPatternAnalyzer()
    fusion_engine = MultimodalFusionEngine()

    print(f"Vision Model Status: {vision_model.status.value}")
    print("Text Analyzer Status: READY")

    # Load raw text mapping for validation set
    raw_text_map: dict[str, str] = {}
    for p in (repo_root / "datasets/raw").glob("**/*raw_samples*.json"):
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                s_id = item.get("sample_id")
                rec_id = item.get("source_record_id")
                txt = item.get("text_description") or item.get("description") or ""
                if s_id:
                    raw_text_map[s_id] = txt
                if rec_id:
                    raw_text_map[rec_id] = txt

    # =========================================================================
    # Step 2: Evaluate on Curated Validation Set (n=119)
    # =========================================================================
    val_file = repo_root / "datasets/training_v1/splits/validation.jsonl"
    val_samples: list[dict[str, Any]] = []
    with open(val_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                val_samples.append(json.loads(line))

    print(f"\nEvaluating on Curated Validation Set (n={len(val_samples)})...")

    # Precompute unimodal inferences on validation set
    val_inferences: list[dict[str, Any]] = []
    for s in val_samples:
        gt = s.get("primary_category")
        img_path = repo_root / s["local_path"]
        img_bytes = img_path.read_bytes()

        v_start = time.perf_counter()
        v_pred = vision_model.predict(img_bytes)
        v_dur = (time.perf_counter() - v_start) * 1000

        txt = (
            raw_text_map.get(s.get("sample_id"))
            or raw_text_map.get(s.get("source_record_id"))
            or ""
        )
        t_start = time.perf_counter()
        t_res = text_analyzer.analyze(txt)
        t_dur = (time.perf_counter() - t_start) * 1000

        t_probs = t_res.get("class_probabilities") or text_result_to_probabilities(
            t_res
        )

        val_inferences.append(
            {
                "sample_id": s.get("sample_id"),
                "ground_truth": gt,
                "vision_pred": v_pred,
                "vision_time_ms": v_dur,
                "text_res": t_res,
                "text_probs": t_probs,
                "text_time_ms": t_dur,
            }
        )

    # Evaluate Candidate Configurations on Validation Set
    candidate_configs: dict[str, FusionConfig] = {
        "text_dominant": FusionConfig(
            name="text_dominant",
            text_weight=0.70,
            vision_weight=0.30,
            disagreement_penalty=0.15,
            temperature=1.0,
            confidence_adaptive=False,
        ),
        "vision_assisted": FusionConfig(
            name="vision_assisted",
            text_weight=0.60,
            vision_weight=0.40,
            disagreement_penalty=0.15,
            temperature=1.0,
            confidence_adaptive=False,
        ),
        "balanced": FusionConfig(
            name="balanced",
            text_weight=0.50,
            vision_weight=0.50,
            disagreement_penalty=0.15,
            temperature=1.0,
            confidence_adaptive=False,
        ),
        "confidence_adaptive": FusionConfig(
            name="confidence_adaptive",
            text_weight=0.50,
            vision_weight=0.50,
            disagreement_penalty=0.15,
            temperature=1.0,
            confidence_adaptive=True,
        ),
    }

    val_metrics_comparison: dict[str, Any] = {}

    # A. Text-Only Validation Metrics
    to_y_true = [inf["ground_truth"] for inf in val_inferences]
    to_y_pred = [inf["text_res"]["predicted_category"] for inf in val_inferences]
    to_probs = [inf["text_probs"] for inf in val_inferences]
    to_confs = [inf["text_probs"][yp] for inf, yp in zip(val_inferences, to_y_pred)]
    val_metrics_comparison["text_only"] = compute_metrics(
        to_y_true, to_y_pred, to_probs, to_confs, CANONICAL_VISION_CATEGORIES
    )

    # B. Vision-Only Validation Metrics
    vo_y_true = [inf["ground_truth"] for inf in val_inferences]
    vo_y_pred = [inf["vision_pred"].predicted_category for inf in val_inferences]
    vo_probs = [inf["vision_pred"].class_probabilities for inf in val_inferences]
    vo_confs = [inf["vision_pred"].confidence for inf in val_inferences]
    val_metrics_comparison["vision_only"] = compute_metrics(
        vo_y_true, vo_y_pred, vo_probs, vo_confs, CANONICAL_VISION_CATEGORIES
    )

    # C. Candidate Fusions
    for cfg_key, cfg in candidate_configs.items():
        f_y_true = [inf["ground_truth"] for inf in val_inferences]
        f_y_pred = []
        f_probs = []
        f_confs = []
        review_flags = []
        agreements = []

        for inf in val_inferences:
            res = fusion_engine.fuse(inf["vision_pred"], inf["text_res"], config=cfg)
            f_y_pred.append(res.fused_category)
            f_probs.append(res.fused_probabilities)
            f_confs.append(res.fused_confidence)
            review_flags.append(res.requires_review)
            agreements.append(res.category_agreement)

        m = compute_metrics(
            f_y_true, f_y_pred, f_probs, f_confs, CANONICAL_VISION_CATEGORIES
        )
        m["review_rate"] = round(sum(review_flags) / len(review_flags), 4)
        m["agreement_rate"] = round(sum(agreements) / len(agreements), 4)

        # Selective accuracy
        auto_accepted = [
            (yt, yp) for yt, yp, rev in zip(f_y_true, f_y_pred, review_flags) if not rev
        ]
        if auto_accepted:
            m["selective_accuracy"] = round(
                sum(1 for yt, yp in auto_accepted if yt == yp) / len(auto_accepted), 4
            )
            m["auto_accepted_count"] = len(auto_accepted)
        else:
            m["selective_accuracy"] = 0.0
            m["auto_accepted_count"] = 0

        val_metrics_comparison[cfg_key] = m

    print("\n--- Validation Set Results ---")
    print(
        f"{'Mode/Config':<24} | {'Acc':<8} | {'Macro F1':<9} | {'Brier':<8} | {'ECE':<8} | {'Review Rate':<11} | {'Selective Acc'}"
    )
    print("-" * 90)
    for k, v in val_metrics_comparison.items():
        rev_str = (
            f"{v.get('review_rate', 0.0) * 100:.1f}%" if "review_rate" in v else "N/A"
        )
        sel_str = (
            f"{v.get('selective_accuracy', 0.0) * 100:.1f}% ({v.get('auto_accepted_count', 0)})"
            if "selective_accuracy" in v
            else "N/A"
        )
        print(
            f"{k:<24} | {v['accuracy'] * 100:.2f}%  | {v['macro_f1']:.4f}    | {v['brier_score']:.4f}   | {v['ece']:.4f}   | {rev_str:<11} | {sel_str}"
        )

    # Select Best Configuration on Validation Set
    best_cfg_key = max(
        candidate_configs.keys(),
        key=lambda k: (
            val_metrics_comparison[k]["macro_f1"],
            val_metrics_comparison[k]["accuracy"],
        ),
    )
    base_best_cfg = candidate_configs[best_cfg_key]
    print(
        f"\nBest Validation Configuration Selected: '{best_cfg_key}' (Macro F1={val_metrics_comparison[best_cfg_key]['macro_f1']:.4f})"
    )

    # Fit Temperature Scaling on Validation Set for Best Configuration
    best_raw_probs = []
    for inf in val_inferences:
        raw_res = fusion_engine.fuse(
            inf["vision_pred"], inf["text_res"], config=base_best_cfg
        )
        best_raw_probs.append(raw_res.raw_probabilities)

    optimal_t, uncalib_brier, calib_brier = fit_temperature_scaling(
        best_raw_probs,
        [inf["ground_truth"] for inf in val_inferences],
        CANONICAL_VISION_CATEGORIES,
        temp_range=(0.5, 2.5),
        steps=41,
    )
    print(
        f"Optimal Temperature Scaling T={optimal_t:.2f} (Brier: {uncalib_brier:.4f} -> {calib_brier:.4f})"
    )

    # Calibrated Final Selected Config
    final_selected_config = FusionConfig(
        name=f"{base_best_cfg.name}_calibrated",
        text_weight=base_best_cfg.text_weight,
        vision_weight=base_best_cfg.vision_weight,
        disagreement_penalty=base_best_cfg.disagreement_penalty,
        temperature=optimal_t,
        confidence_adaptive=base_best_cfg.confidence_adaptive,
        min_confidence_threshold=0.60,
        review_agreement_threshold=0.50,
    )

    # Re-evaluate calibrated version on validation set
    calib_y_true = [inf["ground_truth"] for inf in val_inferences]
    calib_y_pred, calib_probs, calib_confs, calib_reviews, calib_agreements = (
        [],
        [],
        [],
        [],
        [],
    )
    for inf in val_inferences:
        res = fusion_engine.fuse(
            inf["vision_pred"], inf["text_res"], config=final_selected_config
        )
        calib_y_pred.append(res.fused_category)
        calib_probs.append(res.fused_probabilities)
        calib_confs.append(res.fused_confidence)
        calib_reviews.append(res.requires_review)
        calib_agreements.append(res.category_agreement)

    val_calibrated_metrics = compute_metrics(
        calib_y_true,
        calib_y_pred,
        calib_probs,
        calib_confs,
        CANONICAL_VISION_CATEGORIES,
    )
    val_calibrated_metrics["review_rate"] = round(
        sum(calib_reviews) / len(calib_reviews), 4
    )
    val_calibrated_metrics["agreement_rate"] = round(
        sum(calib_agreements) / len(calib_agreements), 4
    )
    auto_acc = [
        (yt, yp)
        for yt, yp, rev in zip(calib_y_true, calib_y_pred, calib_reviews)
        if not rev
    ]
    val_calibrated_metrics["selective_accuracy"] = (
        round(sum(1 for yt, yp in auto_acc if yt == yp) / len(auto_acc), 4)
        if auto_acc
        else 0.0
    )
    val_calibrated_metrics["auto_accepted_count"] = len(auto_acc)

    val_metrics_comparison[f"{best_cfg_key}_calibrated"] = val_calibrated_metrics
    print(
        f"Calibrated '{best_cfg_key}': Acc={val_calibrated_metrics['accuracy'] * 100:.2f}%, ECE={val_calibrated_metrics['ece']:.4f}, Brier={val_calibrated_metrics['brier_score']:.4f}"
    )

    # =========================================================================
    # Step 3: Single Evaluation on Frozen Benchmark (n=300)
    # =========================================================================
    print("\nExecuting Single Controlled Evaluation on Frozen Benchmark (n=300)...")

    bm_samples: list[dict[str, Any]] = []
    with open(benchmark_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                bm_samples.append(json.loads(line))

    bm_root = benchmark_file.parent

    # Collect Benchmark Results
    bm_results_text_only = []
    bm_results_vision_only = []
    bm_results_fused = []

    error_analysis_cases: list[dict[str, Any]] = []

    # Telemetry
    bm_latencies_ms: list[float] = []

    for s in bm_samples:
        gt = s["canonical_category"]
        sample_id = s["sample_id"]
        txt = s.get("text_description") or ""

        img_path = bm_root / s["image_rel_path"]
        img_bytes = img_path.read_bytes()

        start_t = time.perf_counter()

        # Text Inference
        t_res = text_analyzer.analyze(txt)
        t_pred = t_res["predicted_category"]
        t_probs = t_res.get("class_probabilities") or text_result_to_probabilities(
            t_res
        )

        # Vision Inference
        v_pred = vision_model.predict(img_bytes)
        v_cat = v_pred.predicted_category or "Other"

        # Fused Inference
        f_res = fusion_engine.fuse(v_pred, t_res, config=final_selected_config)
        total_time_ms = (time.perf_counter() - start_t) * 1000
        bm_latencies_ms.append(total_time_ms)

        bm_results_text_only.append(
            {
                "gt": gt,
                "pred": t_pred,
                "probs": t_probs,
                "conf": t_probs[t_pred],
            }
        )

        bm_results_vision_only.append(
            {
                "gt": gt,
                "pred": v_cat,
                "probs": v_pred.class_probabilities,
                "conf": v_pred.confidence,
            }
        )

        bm_results_fused.append(
            {
                "sample_id": sample_id,
                "gt": gt,
                "pred": f_res.fused_category,
                "probs": f_res.fused_probabilities,
                "conf": f_res.fused_confidence,
                "requires_review": f_res.requires_review,
                "review_reasons": f_res.review_reasons,
                "modality_agreement": f_res.modality_agreement,
                "category_agreement": f_res.category_agreement,
                "disagreement_detected": f_res.disagreement_detected,
                "t_pred": t_pred,
                "v_pred": v_cat,
                "explanation": f_res.explanation,
            }
        )

        # Forensic Categorization
        t_corr = t_pred == gt
        v_corr = v_cat == gt
        f_corr = f_res.fused_category == gt

        case_type: str
        if t_corr and v_corr:
            case_type = "BOTH_CORRECT"
        elif t_corr and not v_corr:
            case_type = "TEXT_CORRECT_VISION_WRONG"
        elif not t_corr and v_corr:
            case_type = "VISION_CORRECT_TEXT_WRONG"
        else:
            case_type = "BOTH_WRONG"

        error_analysis_cases.append(
            {
                "sample_id": sample_id,
                "ground_truth": gt,
                "text_pred": t_pred,
                "vision_pred": v_cat,
                "fused_pred": f_res.fused_category,
                "fused_conf": f_res.fused_confidence,
                "requires_review": f_res.requires_review,
                "case_type": case_type,
                "is_fused_correct": f_corr,
                "text_correct": t_corr,
                "vision_correct": v_corr,
                "category_agreement": f_res.category_agreement,
                "modality_agreement": f_res.modality_agreement,
                "review_reasons": f_res.review_reasons,
                "image_path": str(s["image_rel_path"]),
                "text_snippet": txt[:80],
            }
        )

    # Compute Benchmark Metrics
    bm_to_metrics = compute_metrics(
        [r["gt"] for r in bm_results_text_only],
        [r["pred"] for r in bm_results_text_only],
        [r["probs"] for r in bm_results_text_only],
        [r["conf"] for r in bm_results_text_only],
        CANONICAL_VISION_CATEGORIES,
    )

    bm_vo_metrics = compute_metrics(
        [r["gt"] for r in bm_results_vision_only],
        [r["pred"] for r in bm_results_vision_only],
        [r["probs"] for r in bm_results_vision_only],
        [r["conf"] for r in bm_results_vision_only],
        CANONICAL_VISION_CATEGORIES,
    )

    bm_fused_metrics = compute_metrics(
        [r["gt"] for r in bm_results_fused],
        [r["pred"] for r in bm_results_fused],
        [r["probs"] for r in bm_results_fused],
        [r["conf"] for r in bm_results_fused],
        CANONICAL_VISION_CATEGORIES,
    )

    bm_review_flags = [r["requires_review"] for r in bm_results_fused]
    bm_agreement_flags = [r["category_agreement"] for r in bm_results_fused]
    bm_fused_metrics["review_rate"] = round(
        sum(bm_review_flags) / len(bm_review_flags), 4
    )
    bm_fused_metrics["agreement_rate"] = round(
        sum(bm_agreement_flags) / len(bm_agreement_flags), 4
    )

    bm_auto_accepted = [
        (r["gt"], r["pred"]) for r in bm_results_fused if not r["requires_review"]
    ]
    if bm_auto_accepted:
        bm_fused_metrics["selective_accuracy"] = round(
            sum(1 for yt, yp in bm_auto_accepted if yt == yp) / len(bm_auto_accepted), 4
        )
        bm_fused_metrics["auto_accepted_count"] = len(bm_auto_accepted)
    else:
        bm_fused_metrics["selective_accuracy"] = 0.0
        bm_fused_metrics["auto_accepted_count"] = 0

    sorted_lats = sorted(bm_latencies_ms)
    bm_fused_metrics["latency_ms"] = {
        "mean": round(sum(bm_latencies_ms) / len(bm_latencies_ms), 2),
        "p50": round(sorted_lats[int(len(sorted_lats) * 0.50)], 2),
        "p95": round(sorted_lats[int(len(sorted_lats) * 0.95)], 2),
    }

    # Step 4: Verify Post-Evaluation Benchmark Hash
    post_hash = verify_benchmark_hash(benchmark_file)
    print(f"\nPost-Evaluation Benchmark Hash: {post_hash} [MATCHES / IMMUTABLE]")

    # Print Comparative Benchmark Results
    print("\n" + "=" * 70)
    print("FROZEN BENCHMARK COMPARATIVE RESULTS (n=300)")
    print("=" * 70)
    print(
        f"{'System Evaluated':<32} | {'Accuracy':<10} | {'Macro F1':<10} | {'Brier':<8} | {'ECE'}"
    )
    print("-" * 72)
    print(
        f"{'Existing Baseline (Text+Proto)':<32} | 79.00%     | 0.7854     | N/A      | N/A"
    )
    print(
        f"{'A. Text-Only':<32} | {bm_to_metrics['accuracy'] * 100:.2f}%     | {bm_to_metrics['macro_f1']:.4f}     | {bm_to_metrics['brier_score']:.4f}   | {bm_to_metrics['ece']:.4f}"
    )
    print(
        f"{'B. Vision-Only (MobileNetV3)':<32} | {bm_vo_metrics['accuracy'] * 100:.2f}%     | {bm_vo_metrics['macro_f1']:.4f}     | {bm_vo_metrics['brier_score']:.4f}   | {bm_vo_metrics['ece']:.4f}"
    )
    print(
        f"{'C. Multimodal Fused (Vision-Assist)':<32} | {bm_fused_metrics['accuracy'] * 100:.2f}%     | {bm_fused_metrics['macro_f1']:.4f}     | {bm_fused_metrics['brier_score']:.4f}   | {bm_fused_metrics['ece']:.4f}"
    )

    # Forensic Breakdown
    case_counts = {
        "BOTH_CORRECT": sum(
            1 for c in error_analysis_cases if c["case_type"] == "BOTH_CORRECT"
        ),
        "TEXT_CORRECT_VISION_WRONG": sum(
            1
            for c in error_analysis_cases
            if c["case_type"] == "TEXT_CORRECT_VISION_WRONG"
        ),
        "VISION_CORRECT_TEXT_WRONG": sum(
            1
            for c in error_analysis_cases
            if c["case_type"] == "VISION_CORRECT_TEXT_WRONG"
        ),
        "BOTH_WRONG": sum(
            1 for c in error_analysis_cases if c["case_type"] == "BOTH_WRONG"
        ),
    }
    high_conf_errors = sum(
        1
        for c in error_analysis_cases
        if not c["is_fused_correct"] and c["fused_conf"] >= 0.70
    )

    print("\n--- Cross-Modal Synergy & Error Breakdown ---")
    for ct, cnt in case_counts.items():
        print(f"  {ct:<28}: {cnt} ({cnt / len(error_analysis_cases) * 100:.1f}%)")
    print(f"  High-Confidence Errors (>= 0.70): {high_conf_errors}")
    print(
        f"  Auto-Accepted Samples Count: {bm_fused_metrics['auto_accepted_count']} / 300 (Selective Acc: {bm_fused_metrics['selective_accuracy'] * 100:.2f}%)"
    )
    print(
        f"  Human Review Required Count: {sum(bm_review_flags)} / 300 (Review Rate: {bm_fused_metrics['review_rate'] * 100:.2f}%)"
    )

    # Top Failure Pairs in Fused Model
    fused_confusions: dict[str, int] = {}
    for c in error_analysis_cases:
        if not c["is_fused_correct"]:
            pair = f"{c['ground_truth']} -> {c['fused_pred']}"
            fused_confusions[pair] = fused_confusions.get(pair, 0) + 1

    top_confusions = sorted(fused_confusions.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]

    # Save Output JSON Artifacts
    out_dir = repo_root / "datasets/evaluation_runs/multimodal_fusion_pilot"
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(
        out_dir / "validation_fusion_comparison.json", "w", encoding="utf-8"
    ) as f:
        json.dump(val_metrics_comparison, f, indent=2)

    with open(out_dir / "selected_fusion_config.json", "w", encoding="utf-8") as f:
        json.dump(final_selected_config.model_dump(), f, indent=2)

    with open(out_dir / "benchmark_fusion_eval.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "evaluation_name": "phase_3_5_frozen_benchmark_multimodal_fusion",
                "benchmark_sha256": post_hash,
                "selected_config": final_selected_config.model_dump(),
                "fused_metrics": bm_fused_metrics,
                "text_only_metrics": bm_to_metrics,
                "vision_only_metrics": bm_vo_metrics,
                "case_counts": case_counts,
                "high_confidence_errors": high_conf_errors,
                "top_confusion_pairs": top_confusions,
                "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            f,
            indent=2,
        )

    with open(out_dir / "benchmark_error_analysis.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "case_counts": case_counts,
                "high_confidence_errors": high_conf_errors,
                "top_confusions": top_confusions,
                "cases": error_analysis_cases,
            },
            f,
            indent=2,
        )

    print(f"\nSaved all evaluation artifacts to: {out_dir}")
    print("Evaluation Complete!")


if __name__ == "__main__":
    main()
