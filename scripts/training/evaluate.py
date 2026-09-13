"""CivicSense Model Evaluation & Error Analysis Tool (Phase 3.4).

Evaluates trained MobileNetV3-Small checkpoints against:
  1. Curated Validation Set (datasets/training_v1/splits/validation.jsonl, n=119)
  2. Frozen Evaluation Benchmark (datasets/benchmark_v1/benchmark_dataset.jsonl, n=300)

Verifies benchmark integrity hash before and after evaluation.
Calculates Accuracy, Macro F1, Per-Class Metrics, Confusion Matrix, and structured Error Analysis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import (  # type: ignore[import-untyped]
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from torch.utils.data import DataLoader

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.training.dataset import (
    CANONICAL_CLASSES,
    IDX_TO_CLASS,
    CivicSenseDataset,
)
from scripts.training.model import load_checkpoint

FROZEN_BENCHMARK_HASH = "e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b"


def verify_benchmark_hash(benchmark_file: Path) -> bool:
    """Verify SHA-256 hash of benchmark_dataset.jsonl matches frozen governance invariant."""
    raw_bytes = benchmark_file.read_bytes()
    computed_hash = hashlib.sha256(raw_bytes).hexdigest()
    if computed_hash != FROZEN_BENCHMARK_HASH:
        raise RuntimeError(
            f"BENCHMARK INTEGRITY VIOLATION! Expected: {FROZEN_BENCHMARK_HASH}, Computed: {computed_hash}"
        )
    return True


def run_evaluation(
    checkpoint_path: str | Path,
    dataset_manifest: str | Path,
    output_prefix: str = "validation",
    output_dir: str | Path = "datasets/evaluation_runs/mobilenet_v3_small_pilot",
    batch_size: int = 16,
) -> dict[str, Any]:
    """Execute evaluation and structured error analysis against the specified dataset."""
    ckpt_path = (repo_root / checkpoint_path).resolve()
    ds_path = (repo_root / dataset_manifest).resolve()
    out_dir = (repo_root / output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    is_benchmark = "benchmark_dataset.jsonl" in ds_path.name
    if is_benchmark:
        print(f"Verifying pre-evaluation benchmark integrity hash for {ds_path.name}...")
        verify_benchmark_hash(ds_path)
        print("  --> Benchmark hash verified intact!")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading checkpoint {ckpt_path.name} on {device}...")
    model, _meta = load_checkpoint(ckpt_path, device=str(device))
    model.eval()

    eval_dataset = CivicSenseDataset(ds_path, split="eval", repo_root=repo_root)
    eval_loader = DataLoader(eval_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    print(f"Evaluating {len(eval_dataset)} samples...")

    all_targets: list[int] = []
    all_preds: list[int] = []
    all_confs: list[float] = []
    all_probs: list[list[float]] = []
    sample_details: list[dict[str, Any]] = []

    start_time = time.perf_counter()
    latencies_ms: list[float] = []

    with torch.no_grad():
        for images, targets, sample_ids in eval_loader:
            images = images.to(device)
            targets = targets.to(device)

            b_start = time.perf_counter()
            logits = model(images)
            b_dur = (time.perf_counter() - b_start) * 1000.0
            latencies_ms.append(b_dur / images.size(0))

            probs = torch.softmax(logits, dim=-1)
            confs, preds = torch.max(probs, dim=-1)

            t_list = targets.cpu().tolist()
            p_list = preds.cpu().tolist()
            c_list = confs.cpu().tolist()
            pr_list = probs.cpu().tolist()

            all_targets.extend(t_list)
            all_preds.extend(p_list)
            all_confs.extend(c_list)
            all_probs.extend(pr_list)

            for i in range(len(sample_ids)):
                sample_details.append({
                    "sample_id": sample_ids[i],
                    "true_class": IDX_TO_CLASS[t_list[i]],
                    "pred_class": IDX_TO_CLASS[p_list[i]],
                    "confidence": round(c_list[i], 4),
                    "is_correct": (t_list[i] == p_list[i]),
                    "probabilities": {
                        cat: round(pr_list[i][idx], 4)
                        for idx, cat in enumerate(CANONICAL_CLASSES)
                    },
                })

    total_eval_duration = round(time.perf_counter() - start_time, 3)

    if is_benchmark:
        print("Verifying post-evaluation benchmark integrity hash...")
        verify_benchmark_hash(ds_path)
        print("  --> Benchmark hash verified unchanged!")

    # Compute Metrics
    acc = accuracy_score(all_targets, all_preds)
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        all_targets, all_preds, average="macro", zero_division=0
    )
    p_per, r_per, f1_per, sup_per = precision_recall_fscore_support(
        all_targets, all_preds, average=None, labels=list(range(len(CANONICAL_CLASSES))), zero_division=0
    )

    cm = confusion_matrix(all_targets, all_preds, labels=list(range(len(CANONICAL_CLASSES))))

    per_class_results = {}
    for idx, cat in enumerate(CANONICAL_CLASSES):
        per_class_results[cat] = {
            "precision": round(float(p_per[idx]), 4),
            "recall": round(float(r_per[idx]), 4),
            "f1_score": round(float(f1_per[idx]), 4),
            "support": int(sup_per[idx]),
        }

    # Latency Stats
    mean_latency = round(float(np.mean(latencies_ms)), 2)
    p50_latency = round(float(np.percentile(latencies_ms, 50)), 2)
    p95_latency = round(float(np.percentile(latencies_ms, 95)), 2)

    # Confidence Stats
    correct_confs = [c for c, is_c in zip(all_confs, [t == p for t, p in zip(all_targets, all_preds)], strict=False) if is_c]
    incorrect_confs = [c for c, is_c in zip(all_confs, [t == p for t, p in zip(all_targets, all_preds)], strict=False) if not is_c]
    mean_conf_correct = round(float(np.mean(correct_confs)), 4) if correct_confs else 0.0
    mean_conf_incorrect = round(float(np.mean(incorrect_confs)), 4) if incorrect_confs else 0.0

    # Error Analysis: High-confidence errors and confusion pairs
    high_conf_errors = [
        s for s in sample_details
        if not s["is_correct"] and s["confidence"] >= 0.70
    ]
    low_conf_correct = [
        s for s in sample_details
        if s["is_correct"] and s["confidence"] < 0.50
    ]

    confusion_pairs: dict[str, int] = {}
    for s in sample_details:
        if not s["is_correct"]:
            pair = f"{s['true_class']} -> {s['pred_class']}"
            confusion_pairs[pair] = confusion_pairs.get(pair, 0) + 1
    sorted_confusion_pairs = sorted(confusion_pairs.items(), key=lambda x: x[1], reverse=True)

    results = {
        "evaluation_name": output_prefix,
        "dataset_manifest": str(ds_path),
        "checkpoint_file": ckpt_path.name,
        "total_samples": len(eval_dataset),
        "accuracy": round(float(acc), 4),
        "macro_precision": round(float(p_macro), 4),
        "macro_recall": round(float(r_macro), 4),
        "macro_f1": round(float(f1_macro), 4),
        "per_class": per_class_results,
        "confusion_matrix": {
            "classes": CANONICAL_CLASSES,
            "matrix": cm.tolist(),
        },
        "latency_ms": {
            "mean": mean_latency,
            "p50": p50_latency,
            "p95": p95_latency,
            "device": str(device),
        },
        "confidence_stats": {
            "mean_confidence_overall": round(float(np.mean(all_confs)), 4),
            "mean_confidence_correct": mean_conf_correct,
            "mean_confidence_incorrect": mean_conf_incorrect,
        },
        "error_analysis_summary": {
            "total_errors": len(all_targets) - sum(t == p for t, p in zip(all_targets, all_preds, strict=False)),
            "high_confidence_errors_count": len(high_conf_errors),
            "low_confidence_correct_count": len(low_conf_correct),
            "top_confusion_pairs": sorted_confusion_pairs[:8],
        },
        "evaluated_at": datetime.now(UTC).isoformat(),
        "evaluation_duration_sec": total_eval_duration,
    }

    # Save detailed JSON evaluation report
    eval_file = out_dir / f"{output_prefix}_eval.json"
    eval_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Save detailed error sample list
    errors_file = out_dir / f"{output_prefix}_error_details.json"
    errors_data = {
        "evaluation_name": output_prefix,
        "high_confidence_errors": high_conf_errors,
        "low_confidence_correct": low_conf_correct,
        "all_incorrect_samples": [s for s in sample_details if not s["is_correct"]],
    }
    errors_file.write_text(json.dumps(errors_data, indent=2), encoding="utf-8")

    print("============================================================")
    print(f"EVALUATION COMPLETE: {output_prefix.upper()}")
    print("============================================================")
    print(f"Samples Evaluated : {len(eval_dataset)}")
    print(f"Accuracy           : {acc*100:.2f}%")
    print(f"Macro F1           : {f1_macro:.4f}")
    print(f"Macro Precision    : {p_macro:.4f}")
    print(f"Macro Recall       : {r_macro:.4f}")
    mean_conf_overall = round(float(np.mean(all_confs)), 4)
    print(f"Mean Latency       : {mean_latency} ms / image")
    print(f"Mean Confidence    : {mean_conf_overall:.4f}")
    print("------------------------------------------------------------")
    print("Per-Class Breakdown:")
    for cat in CANONICAL_CLASSES:
        m = per_class_results[cat]
        print(f"  {cat:15s}: F1={m['f1_score']:.4f} | Prec={m['precision']:.4f} | Rec={m['recall']:.4f} | Supp={m['support']}")
    print(f"Saved report to: {eval_file}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CivicSense Model Evaluation Runner")
    parser.add_argument("--checkpoint", required=True, help="Path to checkpoint .pt file")
    parser.add_argument("--dataset", required=True, help="Path to dataset .jsonl file")
    parser.add_argument("--output-prefix", default="eval", help="Prefix for output report files")
    parser.add_argument("--output-dir", default="datasets/evaluation_runs/mobilenet_v3_small_pilot", help="Output directory")
    args = parser.parse_args()

    run_evaluation(
        checkpoint_path=args.checkpoint,
        dataset_manifest=args.dataset,
        output_prefix=args.output_prefix,
        output_dir=args.output_dir,
    )
