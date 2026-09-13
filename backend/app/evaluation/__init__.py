"""CivicSense Offline Dataset Evaluation & Benchmarking Package."""

from app.evaluation.evaluator import OfflineDeterministicEvaluator
from app.evaluation.metrics import (
    calculate_classification_metrics,
    calculate_latency_percentiles,
)
from app.evaluation.schema import (
    BenchmarkManifest,
    BenchmarkSplit,
    BoundingBox,
    EvaluationResultRecord,
    EvaluationSample,
)

__all__ = [
    "BenchmarkManifest",
    "BenchmarkSplit",
    "BoundingBox",
    "EvaluationResultRecord",
    "EvaluationSample",
    "OfflineDeterministicEvaluator",
    "calculate_classification_metrics",
    "calculate_latency_percentiles",
]
