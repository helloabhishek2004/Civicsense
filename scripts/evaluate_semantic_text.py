"""CivicSense Phase 4A: Comprehensive Semantic Text Evaluation and Statistical Testing.

Evaluates on the frozen canonical benchmark (datasets/benchmark_v1/benchmark_dataset.jsonl, n=300).
Enforces pre-evaluation and post-evaluation benchmark SHA-256 hash checks.
"""

import hashlib
import json
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

# Ensure repo root and backend are in sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "backend"))

import numpy as np
from app.evaluation.calibration import (
    calculate_brier_score,
    calculate_ece,
    calculate_nll,
)
from app.evaluation.statistical_testing import (
    mcnemar_paired_test,
    paired_bootstrap_intervals,
)
from app.services.ai.ensemble_text_model import EnsembleTextModel
from app.services.ai.semantic_text_classifier import SemanticTextClassifier
from app.services.ai.semantic_text_encoder import MiniLMTextEncoder
from app.services.ai.text_analyzer import PrototypeTextModel
from app.services.ai.text_interface import CANONICAL_TEXT_CATEGORIES
from app.services.ai.tfidf_text_classifier import TFIDFTextClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

BENCHMARK_FILE = repo_root / "datasets/benchmark_v1/benchmark_dataset.jsonl"
EXPECTED_BENCHMARK_HASH = "e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b"


def verify_benchmark_hash() -> str:
    current_hash = hashlib.sha256(BENCHMARK_FILE.read_bytes()).hexdigest()
    if current_hash != EXPECTED_BENCHMARK_HASH:
        raise ValueError(
            f"BENCHMARK INTEGRITY VIOLATION! Expected {EXPECTED_BENCHMARK_HASH}, got {current_hash}"
        )
    return current_hash


def evaluate_system(
    model: Any,
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate a text model over the benchmark samples."""
    y_true = [s["canonical_category"] for s in samples]
    texts = [s["text_description"] for s in samples]

    predictions: list[str] = []
    probabilities: list[dict[str, float]] = []
    confidences: list[float] = []

    for txt in texts:
        pred = model.predict(txt)
        predictions.append(pred.predicted_category)
        probabilities.append(pred.probabilities)
        confidences.append(pred.confidence)

    acc = float(accuracy_score(y_true, predictions))
    macro_f1 = float(f1_score(y_true, predictions, average="macro", zero_division=0.0))
    macro_p = float(precision_score(y_true, predictions, average="macro", zero_division=0.0))
    macro_r = float(recall_score(y_true, predictions, average="macro", zero_division=0.0))

    # Per-class metrics
    per_class = {}
    for c in CANONICAL_TEXT_CATEGORIES:
        y_true_binary = [1 if y == c else 0 for y in y_true]
        y_pred_binary = [1 if p == c else 0 for p in predictions]
        p = float(precision_score(y_true_binary, y_pred_binary, zero_division=0.0))
        r = float(recall_score(y_true_binary, y_pred_binary, zero_division=0.0))
        f = float(f1_score(y_true_binary, y_pred_binary, zero_division=0.0))
        support = sum(y_true_binary)
        per_class[c] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f, 4),
            "support": support,
        }

    # Confusion matrix
    cm = confusion_matrix(y_true, predictions, labels=CANONICAL_TEXT_CATEGORIES).tolist()

    # Calibration metrics
    brier = calculate_brier_score(y_true, probabilities, CANONICAL_TEXT_CATEGORIES)
    nll = calculate_nll(y_true, probabilities, CANONICAL_TEXT_CATEGORIES)
    ece, ece_bins = calculate_ece(y_true, predictions, confidences, num_bins=10)

    # Confidence discrimination
    correct_confs = [c for c, yt, yp in zip(confidences, y_true, predictions) if yt == yp]
    incorrect_confs = [c for c, yt, yp in zip(confidences, y_true, predictions) if yt != yp]
    mean_correct_conf = float(np.mean(correct_confs)) if correct_confs else 0.0
    mean_incorrect_conf = float(np.mean(incorrect_confs)) if incorrect_confs else 0.0
    conf_gap = mean_correct_conf - mean_incorrect_conf

    # High confidence errors
    high_conf_errors = [
        {"sample_id": s["sample_id"], "true": yt, "pred": yp, "conf": conf, "text": txt}
        for s, yt, yp, conf, txt in zip(samples, y_true, predictions, confidences, texts)
        if yt != yp and conf >= 0.70
    ]

    return {
        "accuracy": round(acc, 4),
        "correct_count": int(sum(1 for yt, yp in zip(y_true, predictions) if yt == yp)),
        "total_count": len(y_true),
        "macro_f1": round(macro_f1, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "per_class": per_class,
        "confusion_matrix": cm,
        "brier_score": round(brier, 4),
        "nll": round(nll, 4),
        "ece": round(ece, 4),
        "ece_bins": ece_bins,
        "mean_correct_confidence": round(mean_correct_conf, 4),
        "mean_incorrect_confidence": round(mean_incorrect_conf, 4),
        "confidence_discrimination_gap": round(conf_gap, 4),
        "high_confidence_error_count": len(high_conf_errors),
        "high_confidence_errors": high_conf_errors,
        "predictions": predictions,
        "confidences": confidences,
        "probabilities": probabilities,
    }


def profile_latency_and_memory(
    encoder: MiniLMTextEncoder,
    head: SemanticTextClassifier,
    sample_texts: list[str],
    num_iterations: int = 200,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Profile cold-start, granular stages, and peak memory."""
    # Cold-start measurement
    cold_start_t0 = time.perf_counter()
    _ = MiniLMTextEncoder(repo_root / "models/all_minilm_l6_v2")
    cold_start_ms = (time.perf_counter() - cold_start_t0) * 1000

    # Memory measurement
    tracemalloc.start()
    mem_before = tracemalloc.get_traced_memory()

    test_text = sample_texts[0]
    tok_times = []
    forward_times = []
    pool_times = []
    head_times = []
    total_times = []

    # Warm-up (50 iters)
    for _ in range(50):
        _ = head.predict(test_text)

    # Measurement (200 iters)
    for i in range(num_iterations):
        t = sample_texts[i % len(sample_texts)]
        t_start = time.perf_counter()

        # Tokenization
        t0 = time.perf_counter()
        encoded = encoder.tokenizer(
            t, padding=True, truncation=True, max_length=256, return_tensors="pt"
        )
        t_tok = (time.perf_counter() - t0) * 1000
        tok_times.append(t_tok)

        # Transformer forward pass
        import torch

        t1 = time.perf_counter()
        with torch.no_grad():
            outputs = encoder.model(**encoded)
        t_fwd = (time.perf_counter() - t1) * 1000
        forward_times.append(t_fwd)

        # Pooling
        t2 = time.perf_counter()
        token_embs = outputs.last_hidden_state
        mask = encoded["attention_mask"].unsqueeze(-1).expand(token_embs.size()).float()
        sum_embs = torch.sum(token_embs * mask, dim=1)
        sum_mask = torch.clamp(mask.sum(dim=1), min=1e-9)
        pooled = sum_embs / sum_mask
        norm_emb = torch.nn.functional.normalize(pooled, p=2, dim=1).cpu().numpy()[0]
        t_pool = (time.perf_counter() - t2) * 1000
        pool_times.append(t_pool)

        # Head projection
        t3 = time.perf_counter()
        _ = head.classifier.predict_proba(norm_emb.reshape(1, -1))[0]
        t_head = (time.perf_counter() - t3) * 1000
        head_times.append(t_head)

        t_total = (time.perf_counter() - t_start) * 1000
        total_times.append(t_total)

    mem_after = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    latency_report = {
        "cold_start_ms": round(cold_start_ms, 2),
        "iterations": num_iterations,
        "tokenization_ms": {
            "mean": round(float(np.mean(tok_times)), 4),
            "p50": round(float(np.percentile(tok_times, 50)), 4),
            "p95": round(float(np.percentile(tok_times, 95)), 4),
        },
        "forward_pass_ms": {
            "mean": round(float(np.mean(forward_times)), 4),
            "p50": round(float(np.percentile(forward_times, 50)), 4),
            "p95": round(float(np.percentile(forward_times, 95)), 4),
        },
        "pooling_and_norm_ms": {
            "mean": round(float(np.mean(pool_times)), 4),
            "p50": round(float(np.percentile(pool_times, 50)), 4),
            "p95": round(float(np.percentile(pool_times, 95)), 4),
        },
        "head_projection_ms": {
            "mean": round(float(np.mean(head_times)), 4),
            "p50": round(float(np.percentile(head_times, 50)), 4),
            "p95": round(float(np.percentile(head_times, 95)), 4),
        },
        "total_end_to_end_ms": {
            "mean": round(float(np.mean(total_times)), 4),
            "p50": round(float(np.percentile(total_times, 50)), 4),
            "p95": round(float(np.percentile(total_times, 95)), 4),
        },
    }

    memory_report = {
        "peak_traced_mb": round((mem_after[1] - mem_before[0]) / (1024 * 1024), 2),
        "model_file_size_mb": 90.87,
        "quantized_int8_estimated_mb": 22.7,
        "environment": "CPU Desktop Benchmark (x86_64)",
    }

    return latency_report, memory_report


def run_benchmark_evaluation() -> None:
    print("=================================================================")
    print("CivicSense Phase 4A: Standalone Semantic Text Benchmark Evaluation")
    print("=================================================================")

    # 1. Pre-evaluation Benchmark Integrity Check
    pre_hash = verify_benchmark_hash()
    print(f"Pre-evaluation Benchmark SHA-256 Verified: {pre_hash}")

    # 2. Load Benchmark Samples (n=300)
    samples: list[dict[str, Any]] = []
    with open(BENCHMARK_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    print(f"Loaded benchmark samples: {len(samples)} (50 per class)")

    # 4. Initialize Models
    proto_model = PrototypeTextModel()

    tfidf_model = TFIDFTextClassifier(repo_root / "models/tfidf_baseline/tfidf_classifier.pkl")

    encoder = MiniLMTextEncoder(repo_root / "models/all_minilm_l6_v2")
    minilm_model = SemanticTextClassifier(
        encoder=encoder,
        head_path=repo_root / "models/all_minilm_l6_v2/minilm_classifier_head.pkl",
        strategy="trained_head",
    )
    zs_model = SemanticTextClassifier(encoder=encoder, strategy="zero_shot_prototypes")

    # Load frozen selection manifest
    with open(repo_root / "artifacts/civic_sense_phase_4a/selection_manifest.json") as f:
        sel_manifest = json.load(f)
    champion_alpha = sel_manifest["selected_ensemble"]["champion_alpha"]

    ensemble_champion = EnsembleTextModel(
        deterministic_model=proto_model,
        semantic_model=minilm_model,
        alpha=champion_alpha,
    )
    # Also evaluate balanced ensemble (alpha=0.5) and slight lexical prior (alpha=0.1)
    ensemble_alpha_01 = EnsembleTextModel(
        deterministic_model=proto_model,
        semantic_model=minilm_model,
        alpha=0.1,
    )
    ensemble_alpha_05 = EnsembleTextModel(
        deterministic_model=proto_model,
        semantic_model=minilm_model,
        alpha=0.5,
    )

    # 5. Evaluate Systems
    print("\nEvaluating Systems on Frozen Benchmark (n=300)...")

    res_proto = evaluate_system(proto_model, samples)
    print(f"1. Deterministic Baseline:  Acc = {res_proto['accuracy']*100:.2f}% ({res_proto['correct_count']}/300) | Macro F1 = {res_proto['macro_f1']:.4f}")
    assert res_proto["correct_count"] == 237, f"BASELINE INVARIANT FAILED! Expected 237/300 (79.00%), got {res_proto['correct_count']}"

    res_tfidf = evaluate_system(tfidf_model, samples)
    print(f"2. TF-IDF + Logistic Reg:   Acc = {res_tfidf['accuracy']*100:.2f}% ({res_tfidf['correct_count']}/300) | Macro F1 = {res_tfidf['macro_f1']:.4f}")

    res_zs = evaluate_system(zs_model, samples)
    print(f"3. MiniLM Zero-Shot Proto:  Acc = {res_zs['accuracy']*100:.2f}% ({res_zs['correct_count']}/300) | Macro F1 = {res_zs['macro_f1']:.4f}")

    res_minilm = evaluate_system(minilm_model, samples)
    print(f"4. MiniLM Trained Head:     Acc = {res_minilm['accuracy']*100:.2f}% ({res_minilm['correct_count']}/300) | Macro F1 = {res_minilm['macro_f1']:.4f}")

    res_ens_champ = evaluate_system(ensemble_champion, samples)
    print(f"5. Champion Ensemble (a={champion_alpha:.1f}): Acc = {res_ens_champ['accuracy']*100:.2f}% ({res_ens_champ['correct_count']}/300) | Macro F1 = {res_ens_champ['macro_f1']:.4f}")

    res_ens_01 = evaluate_system(ensemble_alpha_01, samples)
    print(f"6. Ensemble (alpha=0.1):     Acc = {res_ens_01['accuracy']*100:.2f}% ({res_ens_01['correct_count']}/300) | Macro F1 = {res_ens_01['macro_f1']:.4f}")

    res_ens_05 = evaluate_system(ensemble_alpha_05, samples)
    print(f"7. Balanced Ensemble (a=0.5):Acc = {res_ens_05['accuracy']*100:.2f}% ({res_ens_05['correct_count']}/300) | Macro F1 = {res_ens_05['macro_f1']:.4f}")

    # 6. Statistical Significance Testing
    print("\nComputing Paired McNemar Tests & 10,000 Paired Bootstrap CIs...")
    y_true = [s["canonical_category"] for s in samples]

    # Primary Comparison: MiniLM vs Deterministic Baseline
    stat_minilm_vs_proto = mcnemar_paired_test(
        y_true, res_proto["predictions"], res_minilm["predictions"]
    )
    boot_minilm_vs_proto = paired_bootstrap_intervals(
        y_true,
        res_proto["predictions"],
        res_minilm["predictions"],
        CANONICAL_TEXT_CATEGORIES,
        iterations=10000,
        seed=42,
    )

    # Secondary Comparison: TF-IDF vs Deterministic Baseline
    stat_tfidf_vs_proto = mcnemar_paired_test(
        y_true, res_proto["predictions"], res_tfidf["predictions"]
    )
    boot_tfidf_vs_proto = paired_bootstrap_intervals(
        y_true,
        res_proto["predictions"],
        res_tfidf["predictions"],
        CANONICAL_TEXT_CATEGORIES,
        iterations=10000,
        seed=42,
    )

    # Comparison: MiniLM vs TF-IDF
    stat_minilm_vs_tfidf = mcnemar_paired_test(
        y_true, res_tfidf["predictions"], res_minilm["predictions"]
    )

    # Comparison: Ensemble (alpha=0.1) vs Deterministic Baseline
    stat_ens01_vs_proto = mcnemar_paired_test(
        y_true, res_proto["predictions"], res_ens_01["predictions"]
    )
    boot_ens01_vs_proto = paired_bootstrap_intervals(
        y_true,
        res_proto["predictions"],
        res_ens_01["predictions"],
        CANONICAL_TEXT_CATEGORIES,
        iterations=10000,
        seed=42,
    )

    diff_metric = boot_minilm_vs_proto["metrics"]["accuracy_difference_pp"]
    print(f"  Accuracy Difference 95% CI: [{diff_metric['ci_95_low']:.2f} pp, {diff_metric['ci_95_high']:.2f} pp]")

    # 7. Latency and Memory Profiling
    print("\nProfiling Execution Latency & Memory Footprint (200 iters)...")
    benchmark_texts = [s["text_description"] for s in samples]
    latency_report, memory_report = profile_latency_and_memory(
        encoder, minilm_model, benchmark_texts, num_iterations=200
    )
    print(f"  Mean Total Latency: {latency_report['total_end_to_end_ms']['mean']:.2f} ms (p50: {latency_report['total_end_to_end_ms']['p50']:.2f} ms, p95: {latency_report['total_end_to_end_ms']['p95']:.2f} ms)")
    print(f"  Peak Traced Memory: {memory_report['peak_traced_mb']:.2f} MB")

    # 8. Subgroup Forensics
    print("\nAnalyzing Subgroup Performance...")
    subgroups = {}

    # Define indices
    from scripts.audit_text_provenance import (
        classify_text_source_type,
        detect_class_keywords,
    )

    idx_all = list(range(len(samples)))
    idx_kw = []
    idx_kw_free = []
    idx_citizen = []
    idx_metadata = []

    for i, s in enumerate(samples):
        txt = s["text_description"]
        cat = s["canonical_category"]
        has_kw, _ = detect_class_keywords(txt, cat)
        st = classify_text_source_type(txt, s.get("source_dataset", ""))

        if has_kw:
            idx_kw.append(i)
        else:
            idx_kw_free.append(i)

        if st == "Citizen-like description":
            idx_citizen.append(i)
        elif st in ("Structured category label", "Metadata title"):
            idx_metadata.append(i)

    def eval_subgroup(indices: list[int], name: str) -> dict[str, Any]:
        if not indices:
            return {"count": 0}
        sub_y_true = [y_true[i] for i in indices]
        sub_proto = [res_proto["predictions"][i] for i in indices]
        sub_tfidf = [res_tfidf["predictions"][i] for i in indices]
        sub_minilm = [res_minilm["predictions"][i] for i in indices]
        sub_ens = [res_ens_01["predictions"][i] for i in indices]

        return {
            "count": len(indices),
            "deterministic_accuracy": round(float(accuracy_score(sub_y_true, sub_proto)), 4),
            "tfidf_accuracy": round(float(accuracy_score(sub_y_true, sub_tfidf)), 4),
            "minilm_accuracy": round(float(accuracy_score(sub_y_true, sub_minilm)), 4),
            "ensemble_accuracy": round(float(accuracy_score(sub_y_true, sub_ens)), 4),
            "minilm_lift_over_deterministic_pp": round(
                (float(accuracy_score(sub_y_true, sub_minilm)) - float(accuracy_score(sub_y_true, sub_proto))) * 100, 2
            ),
        }

    subgroups["all_samples"] = eval_subgroup(idx_all, "All Samples")
    subgroups["keyword_containing"] = eval_subgroup(idx_kw, "Keyword Containing")
    subgroups["keyword_free"] = eval_subgroup(idx_kw_free, "Keyword Free")
    subgroups["citizen_like"] = eval_subgroup(idx_citizen, "Citizen-like")
    subgroups["metadata_rich"] = eval_subgroup(idx_metadata, "Metadata-Rich")

    for sg_name, sg_val in subgroups.items():
        print(f"  [{sg_name}] n={sg_val['count']} -> Det: {sg_val.get('deterministic_accuracy', 0)*100:.1f}% | TF-IDF: {sg_val.get('tfidf_accuracy', 0)*100:.1f}% | MiniLM: {sg_val.get('minilm_accuracy', 0)*100:.1f}% (Lift: {sg_val.get('minilm_lift_over_deterministic_pp', 0):+.1f} pp)")

    # 9. Post-evaluation Benchmark Integrity Check
    post_hash = verify_benchmark_hash()
    print(f"\nPost-evaluation Benchmark SHA-256 Verified: {post_hash}")
    assert pre_hash == post_hash == EXPECTED_BENCHMARK_HASH

    # 10. Save JSON Artifacts
    artifacts_dir = repo_root / "artifacts/civic_sense_phase_4a"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Benchmark results JSON
    benchmark_results = {
        "benchmark_file": str(BENCHMARK_FILE.relative_to(repo_root)),
        "benchmark_sha256": post_hash,
        "sample_count": len(samples),
        "systems": {
            "deterministic_text_baseline": {k: v for k, v in res_proto.items() if k not in ("predictions", "confidences", "probabilities")},
            "tfidf_baseline": {k: v for k, v in res_tfidf.items() if k not in ("predictions", "confidences", "probabilities")},
            "minilm_zero_shot": {k: v for k, v in res_zs.items() if k not in ("predictions", "confidences", "probabilities")},
            "minilm_trained_head": {k: v for k, v in res_minilm.items() if k not in ("predictions", "confidences", "probabilities")},
            "champion_ensemble_alpha_0_0": {k: v for k, v in res_ens_champ.items() if k not in ("predictions", "confidences", "probabilities")},
            "ensemble_alpha_0_1": {k: v for k, v in res_ens_01.items() if k not in ("predictions", "confidences", "probabilities")},
            "ensemble_alpha_0_5": {k: v for k, v in res_ens_05.items() if k not in ("predictions", "confidences", "probabilities")},
        },
    }
    with open(artifacts_dir / "benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    # Statistical tests JSON
    statistical_tests = {
        "primary_comparison": {
            "contrast": "MiniLM (Trained Head) vs Deterministic Text Baseline",
            "mcnemar": stat_minilm_vs_proto.to_dict(),
            "bootstrap_10000_intervals": boot_minilm_vs_proto,
        },
        "secondary_comparisons": {
            "tfidf_vs_deterministic": {
                "mcnemar": stat_tfidf_vs_proto.to_dict(),
                "bootstrap": boot_tfidf_vs_proto,
            },
            "minilm_vs_tfidf": {
                "mcnemar": stat_minilm_vs_tfidf.to_dict(),
            },
            "ensemble_alpha_0_1_vs_deterministic": {
                "mcnemar": stat_ens01_vs_proto.to_dict(),
                "bootstrap": boot_ens01_vs_proto,
            },
        },
    }
    with open(artifacts_dir / "statistical_tests.json", "w", encoding="utf-8") as f:
        json.dump(statistical_tests, f, indent=2)

    # Calibration report JSON
    calibration_report = {
        "deterministic_baseline": {
            "brier_score": res_proto["brier_score"],
            "nll": res_proto["nll"],
            "ece": res_proto["ece"],
            "mean_correct_conf": res_proto["mean_correct_confidence"],
            "mean_incorrect_conf": res_proto["mean_incorrect_confidence"],
            "confidence_gap": res_proto["confidence_discrimination_gap"],
            "high_conf_errors": res_proto["high_confidence_error_count"],
        },
        "tfidf_baseline": {
            "brier_score": res_tfidf["brier_score"],
            "nll": res_tfidf["nll"],
            "ece": res_tfidf["ece"],
            "mean_correct_conf": res_tfidf["mean_correct_confidence"],
            "mean_incorrect_conf": res_tfidf["mean_incorrect_confidence"],
            "confidence_gap": res_tfidf["confidence_discrimination_gap"],
            "high_conf_errors": res_tfidf["high_confidence_error_count"],
        },
        "minilm_trained_head": {
            "brier_score": res_minilm["brier_score"],
            "nll": res_minilm["nll"],
            "ece": res_minilm["ece"],
            "mean_correct_conf": res_minilm["mean_correct_confidence"],
            "mean_incorrect_conf": res_minilm["mean_incorrect_confidence"],
            "confidence_gap": res_minilm["confidence_discrimination_gap"],
            "high_conf_errors": res_minilm["high_confidence_error_count"],
        },
    }
    with open(artifacts_dir / "calibration_report.json", "w", encoding="utf-8") as f:
        json.dump(calibration_report, f, indent=2)

    with open(artifacts_dir / "latency_report.json", "w", encoding="utf-8") as f:
        json.dump(latency_report, f, indent=2)

    with open(artifacts_dir / "memory_report.json", "w", encoding="utf-8") as f:
        json.dump(memory_report, f, indent=2)

    with open(artifacts_dir / "subgroup_analysis.json", "w", encoding="utf-8") as f:
        json.dump(subgroups, f, indent=2)

    print(f"\nAll benchmark JSON artifacts exported cleanly to: {artifacts_dir}")


if __name__ == "__main__":
    run_benchmark_evaluation()
