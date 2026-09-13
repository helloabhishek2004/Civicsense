"""CivicSense Central Evaluation Hardening & Pilot Artifact Freeze Runner.

Workstream Orchestration:
1. Benchmark SHA-256 pre-evaluation integrity verification
2. Single reproducible evaluation of frozen benchmark (n=300)
3. McNemar paired significance testing
4. Paired bootstrap confidence intervals (10,000 iterations, seed=42)
5. Coverage-risk curve sweeping & policy ablation
6. Calibration audit (Brier, ECE, NLL, reliability diagrams)
7. Class-wise forensics and cross-modal trade-offs
8. Latency profiling integration
9. Artifact bundle generation under artifacts/civic_sense_pilot_v0.3.5/
10. Benchmark SHA-256 post-evaluation integrity verification
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import torch

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "backend"))
sys.path.insert(0, str(repo_root))

from app.evaluation.calibration import (
    calculate_brier_score,
    calculate_ece,
    calculate_nll,
)
from app.evaluation.coverage_risk import (
    export_coverage_risk_csv,
    generate_coverage_risk_curve,
)
from app.evaluation.statistical_testing import (
    calculate_selective_confidence_bounds,
    mcnemar_paired_test,
    paired_bootstrap_intervals,
)
from app.services.ai.fusion_engine import (
    CANONICAL_VISION_CATEGORIES,
    FusionConfig,
    MultimodalFusionEngine,
)
from app.services.ai.real_vision_model import RealVisionModel
from app.services.ai.text_analyzer import (
    PrototypeTextPatternAnalyzer,
    text_result_to_probabilities,
)

from scripts.audit_latency_profile import profile_pipeline

EXPECTED_BENCHMARK_HASH = (
    "e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b"
)


def verify_benchmark_hash(path: Path) -> str:
    """Verify cryptographic byte-level integrity of the frozen benchmark."""
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file missing: {path}")
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    if h != EXPECTED_BENCHMARK_HASH:
        raise ValueError(
            f"BENCHMARK INTEGRITY VIOLATION! Expected {EXPECTED_BENCHMARK_HASH}, got {h}"
        )
    return h


def compute_per_class_metrics(
    y_true: list[str],
    y_pred: list[str],
    classes: list[str],
) -> dict[str, dict[str, Any]]:
    """Compute per-class precision, recall, F1, TP, FP, FN, support."""
    res: dict[str, dict[str, Any]] = {}
    for c in classes:
        tp = sum(1 for yt, yp in zip(y_true, y_pred, strict=False) if yt == c and yp == c)
        fp = sum(1 for yt, yp in zip(y_true, y_pred, strict=False) if yt != c and yp == c)
        fn = sum(1 for yt, yp in zip(y_true, y_pred, strict=False) if yt == c and yp != c)
        supp = sum(1 for yt in y_true if yt == c)
        prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = round(2 * prec * rec / (prec + rec), 4) if (prec + rec) > 0 else 0.0
        res[c] = {
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "support": supp,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    return res


def compute_confusion_matrix(
    y_true: list[str],
    y_pred: list[str],
    classes: list[str],
) -> list[list[int]]:
    """Generate 2D confusion matrix."""
    c_to_idx = {c: i for i, c in enumerate(classes)}
    matrix = [[0] * len(classes) for _ in range(len(classes))]
    for yt, yp in zip(y_true, y_pred, strict=False):
        if yt in c_to_idx and yp in c_to_idx:
            matrix[c_to_idx[yt]][c_to_idx[yp]] += 1
    return matrix


def get_git_commit_sha() -> str:
    """Retrieve git commit SHA if available."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8").strip()
    except (subprocess.SubprocessError, OSError):
        return "git_commit_unavailable"


def main() -> None:
    print("=" * 80)
    print("CivicSense Phase 3.5.1 — Evaluation Hardening & Pilot Artifact Freeze")
    print("=" * 80)

    benchmark_path = repo_root / "datasets/benchmark_v1/benchmark_dataset.jsonl"
    bm_root = benchmark_path.parent
    ckpt_path = repo_root / "models/mobilenet_v3_small_v1/exp_b/exp_b_best.pt"
    artifact_dir = repo_root / "artifacts/civic_sense_pilot_v0.3.5"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # 1. Pre-Evaluation Benchmark Hash Verification
    pre_hash = verify_benchmark_hash(benchmark_path)
    print(f"[1/10] Pre-Evaluation Benchmark Hash: {pre_hash} [VERIFIED IMMUTABLE]")

    # 2. Setup Frozen Models & Configuration
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Model checkpoint missing at: {ckpt_path}")

    vision_model = RealVisionModel(checkpoint_path=ckpt_path)
    text_analyzer = PrototypeTextPatternAnalyzer()
    fusion_engine = MultimodalFusionEngine()
    frozen_config = FusionConfig(
        name="vision_assisted_calibrated",
        text_weight=0.6,
        vision_weight=0.4,
        disagreement_penalty=0.15,
        temperature=0.5,
        confidence_adaptive=False,
        min_confidence_threshold=0.60,
        review_agreement_threshold=0.50,
    )
    print(f"[2/10] Loaded Model Checkpoint: {ckpt_path.name}")
    print("       Frozen Fusion Config: text=0.6, vision=0.4, T=0.5, conf_thresh=0.60")

    # 3. Load All 300 Benchmark Samples
    bm_samples: list[dict[str, Any]] = []
    with open(benchmark_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                bm_samples.append(json.loads(line))

    if len(bm_samples) != 300:
        raise ValueError(f"Benchmark sample count corrupted! Expected 300, got {len(bm_samples)}")

    print(f"[3/10] Running Inference on All {len(bm_samples)} Frozen Benchmark Samples...")

    y_true = []
    y_pred_text = []
    y_pred_vision = []
    y_pred_fused = []

    probs_text_list = []
    probs_vision_list = []
    probs_fused_list = []

    confs_text = []
    confs_vision = []
    confs_fused = []

    coverage_risk_sample_records = []
    overturned_cases = []
    high_conf_errors = []

    for s in bm_samples:
        gt = s["canonical_category"]
        sample_id = s["sample_id"]
        txt = s.get("text_description") or ""
        img_path = bm_root / s["image_rel_path"]
        img_bytes = img_path.read_bytes()

        # Text Inference
        t_res = text_analyzer.analyze(txt)
        t_pred = t_res["predicted_category"]
        t_probs = t_res.get("class_probabilities") or text_result_to_probabilities(t_res)
        t_conf = t_probs[t_pred]

        # Vision Inference
        v_pred = vision_model.predict(img_bytes)
        v_cat = v_pred.predicted_category or "Other"
        v_probs = v_pred.class_probabilities
        v_conf = v_pred.confidence

        # Fusion Inference
        f_res = fusion_engine.fuse(v_pred, t_res, config=frozen_config)
        f_cat = f_res.fused_category
        f_probs = f_res.fused_probabilities
        f_conf = f_res.fused_confidence

        y_true.append(gt)
        y_pred_text.append(t_pred)
        y_pred_vision.append(v_cat)
        y_pred_fused.append(f_cat)

        probs_text_list.append(t_probs)
        probs_vision_list.append(v_probs)
        probs_fused_list.append(f_probs)

        confs_text.append(t_conf)
        confs_vision.append(v_conf)
        confs_fused.append(f_conf)

        # Record for coverage risk & triage
        rec = {
            "sample_id": sample_id,
            "gt": gt,
            "fused_pred": f_cat,
            "fused_conf": f_conf,
            "category_agreement": f_res.category_agreement,
            "modality_agreement": f_res.modality_agreement,
            "requires_review": f_res.requires_review,
            "review_reasons": f_res.review_reasons,
            "text_pred": t_pred,
            "vision_pred": v_cat,
        }
        coverage_risk_sample_records.append(rec)

        # Check if vision overturned text
        if t_pred != gt and v_cat == gt:
            overturned_cases.append({
                "sample_id": sample_id,
                "gt": gt,
                "text_pred": t_pred,
                "vision_pred": v_cat,
                "fused_pred": f_cat,
                "fused_correct": f_cat == gt,
                "fused_conf": f_conf,
                "text_snippet": txt[:60],
            })

        if f_cat != gt and f_conf >= 0.70:
            high_conf_errors.append(rec)

    # Verify Reproductibility Numbers
    acc_text = sum(1 for yt, yp in zip(y_true, y_pred_text) if yt == yp) / len(y_true)
    acc_vision = sum(1 for yt, yp in zip(y_true, y_pred_vision) if yt == yp) / len(y_true)
    acc_fused = sum(1 for yt, yp in zip(y_true, y_pred_fused) if yt == yp) / len(y_true)

    auto_acc_count = sum(1 for r in coverage_risk_sample_records if not r["requires_review"])
    auto_acc_correct = sum(
        1 for r in coverage_risk_sample_records if not r["requires_review"] and r["gt"] == r["fused_pred"]
    )

    print(f"       Reproduced Text Baseline: {acc_text*100:.2f}% ({sum(1 for yt, yp in zip(y_true, y_pred_text) if yt == yp)}/300)")
    print(f"       Reproduced Vision Model:  {acc_vision*100:.2f}% ({sum(1 for yt, yp in zip(y_true, y_pred_vision) if yt == yp)}/300)")
    print(f"       Reproduced Multimodal:   {acc_fused*100:.2f}% ({sum(1 for yt, yp in zip(y_true, y_pred_fused) if yt == yp)}/300)")
    print(f"       Reproduced Selective:    {auto_acc_count}/300 accepted, {auto_acc_correct}/{auto_acc_count} correct (100.0%)")

    assert math.isclose(acc_text, 0.7900, abs_tol=1e-3), f"Text acc mismatch: {acc_text}"
    assert math.isclose(acc_vision, 0.4333, abs_tol=1e-3), f"Vision acc mismatch: {acc_vision}"
    assert math.isclose(acc_fused, 0.7967, abs_tol=1e-3), f"Fused acc mismatch: {acc_fused}"
    assert auto_acc_count == 81 and auto_acc_correct == 81, f"Selective mismatch: {auto_acc_count}, {auto_acc_correct}"

    # 4. McNemar Paired Significance Test
    print("[4/10] Computing McNemar Paired Significance Test...")
    mcnemar_res = mcnemar_paired_test(y_true, y_pred_text, y_pred_fused, cc=True)
    print(f"       Contingency: n11={mcnemar_res.n11_both_correct}, n10={mcnemar_res.n10_text_correct_fusion_wrong}, n01={mcnemar_res.n01_text_wrong_fusion_correct}, n00={mcnemar_res.n00_both_wrong}")
    print(f"       Discordant Total: {mcnemar_res.discordant_total} (Text-correct/Fusion-wrong={mcnemar_res.n10_text_correct_fusion_wrong}, Text-wrong/Fusion-correct={mcnemar_res.n01_text_wrong_fusion_correct})")
    print(f"       Accuracy Delta: {mcnemar_res.accuracy_difference_pp:+.2f} pp, 95% CI: [{mcnemar_res.ci_95_difference_pp[0]:+.2f}, {mcnemar_res.ci_95_difference_pp[1]:+.2f}] pp")
    print(f"       McNemar Method: {mcnemar_res.mcnemar_method}, p-value = {mcnemar_res.p_value:.6f}")
    print(f"       Significant at alpha=0.05: {mcnemar_res.is_statistically_significant}")

    # 5. Paired Bootstrap Confidence Intervals (10,000 iters)
    print("[5/10] Computing Paired Bootstrap Intervals (10,000 iterations, seed=42)...")
    boot_res = paired_bootstrap_intervals(
        y_true, y_pred_text, y_pred_fused, CANONICAL_VISION_CATEGORIES, iterations=10000, seed=42
    )
    diff_ci = boot_res["metrics"]["accuracy_difference_pp"]
    f1_diff_ci = boot_res["metrics"]["macro_f1_difference"]
    print(f"       Accuracy Delta Bootstrap 95% CI: [{diff_ci['ci_95_low']:+.2f}, {diff_ci['ci_95_high']:+.2f}] pp (mean={diff_ci['mean']:+.2f} pp)")
    print(f"       Macro F1 Delta Bootstrap 95% CI: [{f1_diff_ci['ci_95_low']:+.4f}, {f1_diff_ci['ci_95_high']:+.4f}] (mean={f1_diff_ci['mean']:+.4f})")

    # Selective Evaluation Bounds
    selective_bounds = calculate_selective_confidence_bounds(
        total_samples=len(y_true),
        auto_accepted_samples=auto_acc_count,
        correct_auto_accepted=auto_acc_correct,
        confidence_level=0.95,
    )
    print(f"       Selective Coverage 95% CI (Wilson): {selective_bounds['coverage_ci_95_wilson']}")
    print(f"       Selective Accuracy 95% CI (Clopper-Pearson): {selective_bounds['selective_accuracy_ci_95_clopper_pearson']}")

    # 6. Coverage-Risk Curve Sweeping & Operating Points
    print("[6/10] Generating Coverage-Risk Curves & Policy Ablations...")
    sweep_results, ablations, operating_points = generate_coverage_risk_curve(coverage_risk_sample_records)
    csv_str = export_coverage_risk_csv(sweep_results)
    (artifact_dir / "coverage_risk_curve.csv").write_text(csv_str, encoding="utf-8")

    coverage_risk_report = {
        "sweep_results": sweep_results,
        "policy_ablations": ablations,
        "operating_points": {k: v.to_dict() for k, v in operating_points.items()},
        "recommended_pilot_operating_point": "balanced",
    }
    with open(artifact_dir / "coverage_risk_report.json", "w", encoding="utf-8") as f:
        json.dump(coverage_risk_report, f, indent=2)

    # 7. Calibration Audit
    print("[7/10] Auditing Probability Calibration...")
    brier_text = calculate_brier_score(y_true, probs_text_list, CANONICAL_VISION_CATEGORIES)
    brier_vision = calculate_brier_score(y_true, probs_vision_list, CANONICAL_VISION_CATEGORIES)
    brier_fused = calculate_brier_score(y_true, probs_fused_list, CANONICAL_VISION_CATEGORIES)

    nll_text = calculate_nll(y_true, probs_text_list, CANONICAL_VISION_CATEGORIES)
    nll_vision = calculate_nll(y_true, probs_vision_list, CANONICAL_VISION_CATEGORIES)
    nll_fused = calculate_nll(y_true, probs_fused_list, CANONICAL_VISION_CATEGORIES)

    ece_text, bins_text = calculate_ece(y_true, y_pred_text, confs_text, num_bins=10)
    ece_vision, bins_vision = calculate_ece(y_true, y_pred_vision, confs_vision, num_bins=10)
    ece_fused, bins_fused = calculate_ece(y_true, y_pred_fused, confs_fused, num_bins=10)

    calibration_audit_report = {
        "calibration_paradigm": "probability_power_law_entropy_scaling",
        "temperature": 0.5,
        "tuning_split": "in_domain_validation_n119",
        "frozen_benchmark_excluded_from_tuning": True,
        "mathematical_audit": {
            "applied_to": "convex_combination_fused_probabilities",
            "formula": "P_calib(c) = P_raw(c)^(1/T) / sum_j P_raw(j)^(1/T)",
            "is_formal_logit_scaling": False,
            "distinction_note": (
                "Applied at probability level because text analyzer lacks neural logits. "
                "Preserves top-1 category argmax strictly for any T > 0 while concentrating mass."
            ),
        },
        "metrics_summary": {
            "brier_scores": {
                "text_baseline": brier_text,
                "vision_only": brier_vision,
                "fused_calibrated": brier_fused,
            },
            "nll_scores": {
                "text_baseline": nll_text,
                "vision_only": nll_vision,
                "fused_calibrated": nll_fused,
            },
            "ece_scores": {
                "text_baseline": ece_text,
                "vision_only": ece_vision,
                "fused_calibrated": ece_fused,
            },
        },
        "reliability_diagram_bins": {
            "text": bins_text,
            "vision": bins_vision,
            "fused": bins_fused,
        },
    }
    with open(artifact_dir / "calibration_report.json", "w", encoding="utf-8") as f:
        json.dump(calibration_audit_report, f, indent=2)

    # 8. Class-wise Forensics & Trade-off Analysis
    print("[8/10] Computing Class-wise Forensics & Trade-off Metrics...")
    text_per_class = compute_per_class_metrics(y_true, y_pred_text, CANONICAL_VISION_CATEGORIES)
    vision_per_class = compute_per_class_metrics(y_true, y_pred_vision, CANONICAL_VISION_CATEGORIES)
    fused_per_class = compute_per_class_metrics(y_true, y_pred_fused, CANONICAL_VISION_CATEGORIES)

    matrix_text = compute_confusion_matrix(y_true, y_pred_text, CANONICAL_VISION_CATEGORIES)
    matrix_vision = compute_confusion_matrix(y_true, y_pred_vision, CANONICAL_VISION_CATEGORIES)
    matrix_fused = compute_confusion_matrix(y_true, y_pred_fused, CANONICAL_VISION_CATEGORIES)

    class_deltas = {}
    for c in CANONICAL_VISION_CATEGORIES:
        t_f1 = text_per_class[c]["f1_score"]
        f_f1 = fused_per_class[c]["f1_score"]
        class_deltas[c] = {
            "text_precision": text_per_class[c]["precision"],
            "text_recall": text_per_class[c]["recall"],
            "text_f1": t_f1,
            "fused_precision": fused_per_class[c]["precision"],
            "fused_recall": fused_per_class[c]["recall"],
            "fused_f1": f_f1,
            "delta_f1": round(f_f1 - t_f1, 4),
            "delta_recall": round(fused_per_class[c]["recall"] - text_per_class[c]["recall"], 4),
        }

    classwise_analysis = {
        "classes": CANONICAL_VISION_CATEGORIES,
        "class_performance": class_deltas,
        "text_per_class": text_per_class,
        "vision_per_class": vision_per_class,
        "fused_per_class": fused_per_class,
        "confusion_matrices": {
            "text": matrix_text,
            "vision": matrix_vision,
            "fused": matrix_fused,
        },
        "overturned_cases_count": len(overturned_cases),
        "overturned_cases": overturned_cases,
        "high_confidence_errors_count": len(high_conf_errors),
        "high_confidence_errors": high_conf_errors,
        "weight_recommendation": {
            "recommendation": "retain_global_weights_and_conservative_review",
            "justification": (
                "Class-specific weights risk severe benchmark overfitting on n=300. "
                "Global weights (0.6 text / 0.4 vision) with strict safety interception (73% review rate) "
                "achieve empirical lift while containing risk."
            ),
        },
    }
    with open(artifact_dir / "classwise_analysis.json", "w", encoding="utf-8") as f:
        json.dump(classwise_analysis, f, indent=2)

    # 9. Granular Latency Profiling
    print("[9/10] Executing Latency Profiling Suite...")
    _ = profile_pipeline(
        warmup_iters=50,
        measured_iters=200,
        export_path=artifact_dir / "latency_report.json",
    )

    # Benchmark Results JSON & Manifest
    benchmark_results = {
        "benchmark_sha256": pre_hash,
        "sample_count": len(y_true),
        "text_accuracy": round(acc_text, 4),
        "vision_accuracy": round(acc_vision, 4),
        "fused_accuracy": round(acc_fused, 4),
        "accuracy_lift_pp": round((acc_fused - acc_text) * 100.0, 4),
        "additional_correct_samples": sum(1 for yt, yp in zip(y_true, y_pred_fused) if yt == yp) - sum(1 for yt, yp in zip(y_true, y_pred_text) if yt == yp),
        "selective_triage": {
            "auto_accepted_count": auto_acc_count,
            "auto_accepted_correct": auto_acc_correct,
            "selective_accuracy": 1.0,
            "human_review_count": len(y_true) - auto_acc_count,
            "review_rate": round((len(y_true) - auto_acc_count) / len(y_true), 4),
            "observed_false_dispatches": 0,
        },
    }
    with open(artifact_dir / "benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    with open(artifact_dir / "statistical_tests.json", "w", encoding="utf-8") as f:
        json.dump(mcnemar_res.to_dict(), f, indent=2)

    with open(artifact_dir / "bootstrap_confidence_intervals.json", "w", encoding="utf-8") as f:
        json.dump(boot_res | {"selective_bounds": selective_bounds}, f, indent=2)

    # Evaluation Manifest
    evaluation_manifest = {
        "artifact_version": "v0.3.5",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_commit_sha": get_git_commit_sha(),
        "benchmark": {
            "path": "datasets/benchmark_v1/benchmark_dataset.jsonl",
            "sha256": pre_hash,
            "sample_count": len(y_true),
            "classes": CANONICAL_VISION_CATEGORIES,
        },
        "model": {
            "architecture": "MobileNetV3-Small (1.52M parameters)",
            "checkpoint_path": str(ckpt_path.relative_to(repo_root)),
            "training_experiment": "Phase 3.4 Exp B (Fine-Tuning Last 3 Residual Blocks)",
        },
        "fusion_configuration": frozen_config.model_dump(),
        "evaluation_parameters": {
            "random_seed": 42,
            "bootstrap_iterations": 10000,
            "temperature": 0.5,
        },
        "environment": {
            "os": f"{platform.system()} {platform.release()}",
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "cpu_architecture": platform.processor() or platform.machine(),
        },
        "reproducibility_command": "python scripts/run_phase_3_5_1_hardening.py",
        "known_limitations": [
            "Benchmark size is n=300 (50/class); McNemar paired statistical power is limited.",
            "Observed 100% selective precision (81/81) has an exact Clopper-Pearson 95% lower bound of 96.37%.",
            "Latency is measured on desktop CPU and does not establish Android on-device performance.",
            "Autonomous municipal dispatch is not approved; system must remain paired with officer triage.",
        ],
    }
    with open(artifact_dir / "evaluation_manifest.json", "w", encoding="utf-8") as f:
        json.dump(evaluation_manifest, f, indent=2)

    # README for Artifact Bundle
    readme_content = f"""# CivicSense Pilot Artifact Bundle (v0.3.5)
**Freeze Date**: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}  
**Status**: Frozen and Statistically Validated  
**Benchmark SHA-256**: `{pre_hash}`

## Contents
1. `evaluation_manifest.json`: System provenance, environment, git commit, and hyperparameters.
2. `benchmark_results.json`: Canonical reproduced accuracy, macro F1, and selective triage metrics.
3. `statistical_tests.json`: McNemar paired significance test results and contingency table.
4. `bootstrap_confidence_intervals.json`: 10,000-iteration paired bootstrap intervals and exact selective bounds.
5. `coverage_risk_curve.csv`: Multi-threshold sweep evaluating coverage, selective accuracy, and errors.
6. `coverage_risk_report.json`: Operating points analysis (Conservative, Balanced, High-Coverage) and policy ablations.
7. `calibration_report.json`: Mathematical calibration audit, Brier scores, ECE, NLL, and reliability diagrams.
8. `latency_report.json`: 8-stage micro-benchmarking breakdown across 200 measured iterations.
9. `classwise_analysis.json`: Per-class metrics, confusion matrices, overturned cases, and trade-off analysis.

## Key Conclusions
- **Accuracy Lift**: Fused accuracy is **79.67%** (239/300) vs **79.00%** (237/300) text baseline (+0.67 pp, +2 samples).
- **Statistical Significance**: McNemar p-value is **p = 0.8145** (not statistically significant on n=300).
- **Selective Auto-Triage**: 81 / 300 reports accepted with 100% observed accuracy (81/81 correct, 95% CI: [96.37%, 100.00%]).
- **Deployment Recommendation**: Balanced operating point (tau=0.60, agreement required, Other excluded, 73% review rate). Autonomous dispatch without officer review is NOT approved.
"""
    (artifact_dir / "README.md").write_text(readme_content.strip() + "\n", encoding="utf-8")

    # 10. Post-Evaluation Benchmark Hash Verification
    post_hash = verify_benchmark_hash(benchmark_path)
    print(f"[10/10] Post-Evaluation Benchmark Hash: {post_hash} [VERIFIED IMMUTABLE]")

    print("\n" + "=" * 80)
    print("Phase 3.5.1 Hardening & Artifact Freeze Completed Successfully!")
    print(f"Artifact directory: {artifact_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
