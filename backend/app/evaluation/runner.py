import datetime
import json
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from app.evaluation.evaluator import OfflineDeterministicEvaluator
from app.evaluation.metrics import (
    calculate_classification_metrics,
    calculate_confidence_metrics,
    calculate_latency_percentiles,
    classify_failure_type,
)
from app.evaluation.schema import EvaluationResultRecord, EvaluationSample

CANONICAL_BENCHMARK_CATEGORIES = [
    "Pothole",
    "Road Damage",
    "Garbage",
    "Water Leakage",
    "Streetlight",
    "Other",
]


class BenchmarkRunner:
    """Headless offline benchmark runner.

    Reads benchmark JSONL files, validates samples, runs the offline evaluator,
    and calculates classification, confidence, and telemetry metrics.
    Supports multimodal, vision-only, and text-only evaluation modes.
    """

    def __init__(
        self,
        benchmark_file: str | Path,
        benchmark_root: str | Path | None = None,
        mode: str = "multimodal",
    ) -> None:
        self.benchmark_file = Path(benchmark_file)
        self.benchmark_root = (
            Path(benchmark_root) if benchmark_root else self.benchmark_file.parent
        )
        self.mode = mode.lower()
        self.evaluator = OfflineDeterministicEvaluator()

    def run(
        self,
        mode: str | None = None,
        output_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """Execute evaluation over all samples in the benchmark file."""
        if not self.benchmark_file.exists():
            msg = f"Benchmark file not found at: {self.benchmark_file.resolve()}"
            raise FileNotFoundError(msg)

        active_mode = (mode or self.mode).lower()
        if active_mode not in ["multimodal", "vision_only", "image_only", "text_only"]:
            msg = (
                f"Unsupported evaluation mode '{active_mode}'. "
                "Must be 'multimodal', 'vision_only', or 'text_only'."
            )
            raise ValueError(msg)

        records: list[EvaluationResultRecord] = []
        y_true: list[str] = []
        y_pred: list[str] = []
        review_flags: list[bool] = []
        latencies: list[float] = []

        with open(self.benchmark_file, encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                raw_str = line.strip()
                if not raw_str:
                    continue

                try:
                    raw_data = json.loads(raw_str)
                    sample = EvaluationSample.model_validate(raw_data)
                except Exception as err:
                    msg = f"Malformed sample at line {line_idx}: {err}"
                    raise ValueError(msg) from err

                # Load image bytes if relative path is specified
                image_bytes: bytes | None = None
                if sample.image_rel_path:
                    full_image_path = self.benchmark_root / sample.image_rel_path
                    if full_image_path.exists():
                        image_bytes = full_image_path.read_bytes()

                # Determine inputs based on evaluation mode
                if active_mode in ["vision_only", "image_only"]:
                    eval_image = image_bytes
                    eval_text = None
                    eval_mode_str = "VISION_ONLY"
                elif active_mode == "text_only":
                    eval_image = None
                    eval_text = sample.text_description
                    eval_mode_str = "TEXT_ONLY"
                else:
                    eval_image = image_bytes
                    eval_text = sample.text_description
                    eval_mode_str = "MULTIMODAL"

                # Execute offline evaluator
                sample_start = time.perf_counter()
                prediction = self.evaluator.evaluate(
                    image_bytes=eval_image,
                    text=eval_text,
                )
                sample_dur_ms = round((time.perf_counter() - sample_start) * 1000, 2)

                is_correct = prediction.predicted_category == sample.canonical_category

                failure_type = (
                    classify_failure_type(
                        ground_truth_category=sample.canonical_category,
                        predicted_category=prediction.predicted_category,
                        text_description=sample.text_description,
                        is_blurry=sample.is_blurry,
                        is_low_res=sample.is_low_res,
                        evidence_agreement=prediction.evidence_agreement,
                        pipeline_errors=prediction.warnings,
                    )
                    if not is_correct
                    else None
                )

                record = EvaluationResultRecord(
                    sample_id=sample.sample_id,
                    ground_truth_category=sample.canonical_category,
                    predicted_category=prediction.predicted_category,
                    confidence=prediction.confidence,
                    confidence_tier=prediction.confidence_tier.value,
                    review_required=prediction.requires_review,
                    review_reasons=prediction.review_reasons,
                    latency_ms=sample_dur_ms,
                    is_correct=is_correct,
                    evaluation_mode=eval_mode_str,
                    predicted_severity=prediction.severity.value,
                    ground_truth_severity=None,
                    failure_type=failure_type,
                    model_name=prediction.model_name,
                    model_version=prediction.model_version,
                    pipeline_errors=prediction.warnings,
                    timing_breakdown=prediction.timing_breakdown,
                    decision_explanation=prediction.decision_explanation,
                    evidence_agreement=prediction.evidence_agreement,
                )
                records.append(record)

                y_true.append(sample.canonical_category)
                y_pred.append(prediction.predicted_category)
                review_flags.append(prediction.requires_review)
                latencies.append(sample_dur_ms)

        # Classification metrics
        metrics = calculate_classification_metrics(
            y_true=y_true,
            y_pred=y_pred,
            categories=CANONICAL_BENCHMARK_CATEGORIES,
            review_required_flags=review_flags,
        )

        # Latency statistics
        latency_stats = calculate_latency_percentiles(latencies)

        # Fine-grained stage averages
        stage_names = [
            "intake_validation_ms",
            "vision_inference_ms",
            "text_inference_ms",
            "fusion_ms",
            "decision_ms",
        ]
        stage_averages: dict[str, float] = {}
        for stage in stage_names:
            vals = [
                float(r.timing_breakdown[stage])  # type: ignore[arg-type]
                for r in records
                if r.timing_breakdown and r.timing_breakdown.get(stage) is not None
            ]
            if vals:
                stage_averages[stage] = round(sum(vals) / len(vals), 2)
        latency_stats["stage_breakdown_means_ms"] = stage_averages

        # Confidence analytics
        confidence_stats = calculate_confidence_metrics(
            confidences=[r.confidence for r in records],
            is_correct_flags=[r.is_correct for r in records],
            confidence_tiers=[r.confidence_tier for r in records],
            review_required_flags=[r.review_required for r in records],
        )

        # Severity distribution (ground-truth severity unavailable in benchmark)
        severity_summary = {
            "status": "unavailable",
            "reason": (
                "Ground-truth severity labels are not annotated in benchmark_v1 records. "
                "Predicted severity distribution is reported without ground-truth comparison."
            ),
            "predicted_distribution": dict(Counter(r.predicted_severity for r in records)),
        }

        # Failure counts by type
        failure_counts = dict(
            Counter(r.failure_type for r in records if r.failure_type is not None)
        )

        run_output: dict[str, Any] = {
            "benchmark_file": str(self.benchmark_file),
            "evaluation_mode": active_mode,
            "total_evaluated": len(records),
            "metrics": metrics,
            "confidence": confidence_stats,
            "severity": severity_summary,
            "failures_by_type": failure_counts,
            "latency": latency_stats,
            "results": [r.model_dump() for r in records],
        }

        # Export artifacts if output_dir specified
        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)

            # 1. predictions.jsonl
            with open(out_path / "predictions.jsonl", "w", encoding="utf-8") as f:
                for r in records:
                    f.write(r.model_dump_json() + "\n")

            # 2. metrics.json
            with open(out_path / "metrics.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "classification": metrics,
                        "confidence": confidence_stats,
                        "severity": severity_summary,
                        "failures_by_type": failure_counts,
                    },
                    f,
                    indent=2,
                )

            # 3. confusion_matrix.json
            cm_matrix = metrics["confusion_matrix"]["matrix"]
            cm_classes = metrics["confusion_matrix"]["classes"]
            with open(out_path / "confusion_matrix.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "classes": cm_classes,
                        "matrix": cm_matrix,
                        "row_ground_truth": cm_classes,
                        "col_predicted": cm_classes,
                        "total_samples": len(records),
                        "matrix_sum": sum(sum(row) for row in cm_matrix),
                    },
                    f,
                    indent=2,
                )

            # 4. latency.json
            with open(out_path / "latency.json", "w", encoding="utf-8") as f:
                json.dump(latency_stats, f, indent=2)

            # 5. failures.jsonl
            with open(out_path / "failures.jsonl", "w", encoding="utf-8") as f:
                for r in records:
                    if not r.is_correct:
                        f.write(r.model_dump_json() + "\n")

            # 6. run_metadata.json
            git_commit = "unknown"
            try:
                git_proc = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                if git_proc.returncode == 0:
                    git_commit = git_proc.stdout.strip()
            except Exception:
                pass

            manifest_hash = None
            manifest_file = self.benchmark_root / "manifest.json"
            if manifest_file.exists():
                try:
                    m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    manifest_hash = m_data.get("integrity_hash")
                except Exception:
                    pass

            run_metadata = {
                "run_id": f"baseline_{active_mode}",
                "benchmark_file": str(self.benchmark_file),
                "benchmark_root": str(self.benchmark_root),
                "manifest_integrity_hash": manifest_hash,
                "evaluation_timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                "git_commit": git_commit,
                "python_version": sys.version,
                "platform": platform.platform(),
                "evaluation_mode": active_mode,
                "model_name": "deterministic_demo_processor",
                "model_version": "1.5.0",
                "hardware_acceleration": "NONE",
                "random_seed": None,
                "total_samples_attempted": len(records),
                "total_samples_completed": len(records),
                "total_errors": 0,
                "overall_accuracy": metrics["accuracy"],
                "macro_f1": metrics["macro_f1"],
            }
            with open(out_path / "run_metadata.json", "w", encoding="utf-8") as f:
                json.dump(run_metadata, f, indent=2)

        return run_output
