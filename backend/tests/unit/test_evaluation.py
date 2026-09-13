import datetime
import io
import json
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from app.evaluation.evaluator import OfflineDeterministicEvaluator
from app.evaluation.metrics import (
    calculate_classification_metrics,
    calculate_latency_percentiles,
)
from app.evaluation.runner import CANONICAL_BENCHMARK_CATEGORIES, BenchmarkRunner
from app.evaluation.schema import (
    BenchmarkManifest,
    BenchmarkSplit,
    BoundingBox,
    EvaluationResultRecord,
    EvaluationSample,
)
from app.models.enums import SeverityLevel
from app.services.ai.normalized_prediction import PredictionNormalizer


def _make_test_jpeg_bytes(
    size: tuple[int, int] = (100, 100),
    color: str = "blue",
) -> bytes:
    """Generate in-memory valid JPEG image bytes for unit testing."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ===========================================================================
# 1. SCHEMA VALIDATION TESTS
# ===========================================================================


def test_evaluation_sample_valid() -> None:
    """EvaluationSample accepts valid fields and serializes correctly."""
    sample = EvaluationSample(
        sample_id="test-sample-001",
        image_rel_path="pothole/sample_001.jpg",
        source_dataset="rdd2022",
        source_record_id="Japan_0001",
        canonical_category="Pothole",
        original_category="D00",
        category_confidence=0.98,
        bounding_boxes=[
            BoundingBox(
                label="Pothole",
                x_min=0.1,
                y_min=0.2,
                x_max=0.5,
                y_max=0.6,
            )
        ],
        text_description="Deep pothole in middle of asphalt road",
        split=BenchmarkSplit.BENCHMARK,
        license="CC-BY-SA-4.0",
        license_url="https://creativecommons.org/licenses/by-sa/4.0/",
        attribution="RDD2022 Research Team",
        is_blurry=False,
        is_low_res=False,
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        phash="1001100110011001",
        duplicate_group_id=None,
        review_status="CONFIRMED",
        metadata_json={"weather": "sunny"},
    )

    assert sample.sample_id == "test-sample-001"
    assert sample.canonical_category == "Pothole"
    assert sample.split == BenchmarkSplit.BENCHMARK
    assert len(sample.bounding_boxes) == 1
    assert sample.bounding_boxes[0].x_min == 0.1
    assert sample.bounding_boxes[0].x_max == 0.5


def test_evaluation_sample_invalid_canonical_category_rejected() -> None:
    """Non-canonical category labels must be rejected by Pydantic validator."""
    invalid_categories = ["Trash", "Sinkhole", "Potholes", "Street Light", "rubbish"]

    for cat in invalid_categories:
        with pytest.raises(ValidationError) as exc_info:
            EvaluationSample(
                sample_id="invalid-sample",
                image_rel_path="test.jpg",
                text_description="test",
                source_dataset="test",
                source_record_id="1",
                canonical_category=cat,
                original_category="raw_tag",
                license="MIT",
                license_url="https://opensource.org/licenses/MIT",
                attribution="Tester",
                sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                phash="10011001",
                review_status="CONFIRMED",
            )
        assert "not in authoritative taxonomy" in str(exc_info.value)


def test_bounding_box_coordinates_validation() -> None:
    """BoundingBox rejects invalid coordinates such as x_max < x_min or out of bounds."""
    # Valid box passes
    box = BoundingBox(label="pothole", x_min=0.1, y_min=0.2, x_max=0.8, y_max=0.9)
    assert box.x_max == 0.8

    # x_max < x_min
    with pytest.raises(ValidationError) as exc_info:
        BoundingBox(label="pothole", x_min=0.8, y_min=0.2, x_max=0.3, y_max=0.9)
    assert "x_max" in str(exc_info.value)

    # y_max < y_min
    with pytest.raises(ValidationError) as exc_info:
        BoundingBox(label="pothole", x_min=0.1, y_min=0.9, x_max=0.5, y_max=0.2)
    assert "y_max" in str(exc_info.value)

    # Out of [0.0, 1.0] range
    with pytest.raises(ValidationError):
        BoundingBox(label="pothole", x_min=-0.1, y_min=0.0, x_max=0.5, y_max=0.5)

    with pytest.raises(ValidationError):
        BoundingBox(label="pothole", x_min=0.0, y_min=0.0, x_max=1.2, y_max=0.5)


def test_benchmark_manifest_validation() -> None:
    """BenchmarkManifest validates required fields and metadata counts."""
    manifest = BenchmarkManifest(
        benchmark_version="1.0.0",
        generation_timestamp=datetime.datetime.now(datetime.UTC),
        total_sample_count=300,
        category_counts={
            "Pothole": 50,
            "Road Damage": 50,
            "Garbage": 50,
            "Water Leakage": 50,
            "Streetlight": 50,
            "Other": 50,
        },
        source_dataset_counts={"RDD2022": 100, "TACO": 50},
        image_root="images",
        integrity_hash="sha256:abcd1234efgh5678",
    )

    assert manifest.benchmark_version == "1.0.0"
    assert manifest.total_sample_count == 300
    assert manifest.category_counts["Pothole"] == 50
    assert manifest.schema_version == "1.0.0"


def test_evaluation_result_record_validation() -> None:
    """EvaluationResultRecord serializes inference outcomes accurately."""
    rec = EvaluationResultRecord(
        sample_id="samp-01",
        ground_truth_category="Pothole",
        predicted_category="Pothole",
        confidence=0.85,
        confidence_tier="MEDIUM",
        review_required=False,
        review_reasons=[],
        latency_ms=12.5,
        is_correct=True,
        evaluation_mode="MULTIMODAL",
    )
    assert rec.is_correct is True
    assert rec.latency_ms == 12.5


# ===========================================================================
# 2. METRIC SUITE TESTS
# ===========================================================================


def test_metrics_empty_inputs() -> None:
    """Empty ground truth and prediction lists return zero metrics gracefully."""
    metrics = calculate_classification_metrics([], [])
    assert metrics["total_samples"] == 0
    assert metrics["accuracy"] == 0.0
    assert metrics["macro_f1"] == 0.0
    assert metrics["abstention_rate"] == 0.0
    assert metrics["selective_accuracy"] == 0.0
    assert metrics["confusion_matrix"]["matrix"] == []


def test_metrics_perfect_predictions() -> None:
    """When y_true equals y_pred, precision, recall, accuracy, and F1 equal 1.0."""
    canonical_classes = list(PredictionNormalizer.CATEGORY_LABELS.keys())
    y_true = ["Pothole", "Garbage", "Streetlight"]
    y_pred = ["Pothole", "Garbage", "Streetlight"]

    metrics = calculate_classification_metrics(
        y_true=y_true,
        y_pred=y_pred,
        categories=canonical_classes,
        review_required_flags=[False, False, False],
    )

    assert metrics["total_samples"] == 3
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_precision"] == 1.0
    assert metrics["macro_recall"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["abstention_rate"] == 0.0
    assert metrics["selective_accuracy"] == 1.0

    pothole_metrics = metrics["per_class"]["Pothole"]
    assert pothole_metrics["precision"] == 1.0
    assert pothole_metrics["recall"] == 1.0
    assert pothole_metrics["f1"] == 1.0
    assert pothole_metrics["support"] == 1


def test_metrics_completely_incorrect_predictions() -> None:
    """When all predictions mismatch, accuracy and macro F1 equal 0.0."""
    canonical_classes = list(PredictionNormalizer.CATEGORY_LABELS.keys())
    y_true = ["Pothole", "Garbage"]
    y_pred = ["Streetlight", "Road Damage"]

    metrics = calculate_classification_metrics(
        y_true=y_true,
        y_pred=y_pred,
        categories=canonical_classes,
    )

    assert metrics["total_samples"] == 2
    assert metrics["accuracy"] == 0.0
    assert metrics["macro_f1"] == 0.0
    assert metrics["macro_precision"] == 0.0
    assert metrics["macro_recall"] == 0.0


def test_metrics_missing_classes() -> None:
    """Datasets with missing classes calculate metrics without division by zero or KeyError."""
    canonical_classes = list(PredictionNormalizer.CATEGORY_LABELS.keys())
    # Only 2 of the 6 classes are present in ground truth
    y_true = ["Pothole", "Pothole", "Garbage"]
    y_pred = ["Pothole", "Other", "Garbage"]

    metrics = calculate_classification_metrics(
        y_true=y_true,
        y_pred=y_pred,
        categories=canonical_classes,
    )

    assert metrics["total_samples"] == 3
    assert metrics["accuracy"] == round(2 / 3, 4)
    # Per-class entries must exist for all canonical classes
    assert set(metrics["per_class"].keys()) == set(canonical_classes)
    # Streetlight has support 0
    assert metrics["per_class"]["Streetlight"]["support"] == 0
    assert metrics["per_class"]["Streetlight"]["f1"] == 0.0


def test_metrics_confusion_matrix_ordering() -> None:
    """Confusion matrix classes must strictly follow canonical category ordering."""
    canonical_classes = list(PredictionNormalizer.CATEGORY_LABELS.keys())
    # Pothole is index 0, Garbage is index 2
    y_true = ["Pothole"]
    y_pred = ["Garbage"]

    metrics = calculate_classification_metrics(
        y_true=y_true,
        y_pred=y_pred,
        categories=canonical_classes,
    )

    cm = metrics["confusion_matrix"]
    assert cm["classes"] == canonical_classes
    assert len(cm["matrix"]) == len(canonical_classes)
    assert len(cm["matrix"][0]) == len(canonical_classes)

    pothole_idx = canonical_classes.index("Pothole")
    garbage_idx = canonical_classes.index("Garbage")
    # True Pothole predicted as Garbage
    assert cm["matrix"][pothole_idx][garbage_idx] == 1


def test_metrics_abstention_and_selective_accuracy() -> None:
    """Abstention rate and selective accuracy are computed correctly on flagged subsets."""
    canonical_classes = list(PredictionNormalizer.CATEGORY_LABELS.keys())
    y_true = ["Pothole", "Garbage", "Road Damage", "Streetlight"]
    y_pred = ["Pothole", "Other", "Water Leakage", "Streetlight"]
    # 2 out of 4 require human review (abstained)
    review_flags = [False, True, False, True]

    metrics = calculate_classification_metrics(
        y_true=y_true,
        y_pred=y_pred,
        categories=canonical_classes,
        review_required_flags=review_flags,
    )

    assert metrics["total_samples"] == 4
    # Abstention rate = 2 / 4 = 0.50
    assert metrics["abstention_rate"] == 0.50

    # Unreviewed (accepted) samples are at indices 0 and 2
    # idx 0: Pothole == Pothole (correct)
    # idx 2: Road Damage != Water Leakage (incorrect)
    # Selective accuracy = 1 / 2 = 0.50
    assert metrics["selective_accuracy"] == 0.50


def test_latency_percentile_calculation() -> None:
    """Latency percentile calculation produces expected p50, p95, and p99 values."""
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    percentiles = calculate_latency_percentiles(latencies)

    assert percentiles["p50"] == 55.0
    assert percentiles["p95"] == 95.5
    assert percentiles["p99"] == 99.1

    empty = calculate_latency_percentiles([])
    assert empty["p50"] == 0.0
    assert empty["p95"] == 0.0
    assert empty["p99"] == 0.0


# ===========================================================================
# 3. OFFLINE EVALUATOR TESTS
# ===========================================================================


def test_offline_evaluator_multimodal_execution() -> None:
    """OfflineDeterministicEvaluator evaluates valid image bytes and text deterministically."""
    evaluator = OfflineDeterministicEvaluator()
    img_bytes = _make_test_jpeg_bytes(size=(128, 128))

    prediction = evaluator.evaluate(
        image_bytes=img_bytes,
        text="Severe deep pothole on main road",
    )

    assert prediction.predicted_category in PredictionNormalizer.CATEGORY_LABELS
    assert prediction.confidence > 0.0
    assert prediction.inference_time_ms >= 0
    assert prediction.timing_breakdown.get("vision_inference_ms") is not None
    assert prediction.timing_breakdown.get("text_inference_ms") is not None


def test_offline_evaluator_vision_only_execution() -> None:
    """Vision-only evaluation succeeds without text input."""
    evaluator = OfflineDeterministicEvaluator()
    img_bytes = _make_test_jpeg_bytes(size=(128, 128))

    prediction = evaluator.evaluate(
        image_bytes=img_bytes,
        text=None,
    )

    assert prediction.predicted_category in PredictionNormalizer.CATEGORY_LABELS
    assert prediction.timing_breakdown.get("vision_inference_ms") is not None
    assert prediction.timing_breakdown.get("text_inference_ms") is None


def test_offline_evaluator_text_only_execution() -> None:
    """Text-only evaluation succeeds without image bytes."""
    evaluator = OfflineDeterministicEvaluator()

    prediction = evaluator.evaluate(
        image_bytes=None,
        text="Large pile of garbage dumped beside sidewalk",
    )

    assert prediction.predicted_category == "Garbage"
    assert prediction.timing_breakdown.get("vision_inference_ms") is None
    assert prediction.timing_breakdown.get("text_inference_ms") is not None


def test_offline_evaluator_empty_fallback() -> None:
    """Empty inputs safely fall back to Other category and default confidence."""
    evaluator = OfflineDeterministicEvaluator()

    prediction = evaluator.evaluate(
        image_bytes=None,
        text="",
    )

    assert prediction.predicted_category == "Other"
    assert prediction.severity == SeverityLevel.LOW
    assert prediction.confidence <= 0.40
    assert prediction.requires_review is True


# ===========================================================================
# 4. BENCHMARK RUNNER TESTS
# ===========================================================================


def test_benchmark_runner_missing_file_raises(tmp_path: Path) -> None:
    """BenchmarkRunner raises FileNotFoundError if JSONL file does not exist."""
    missing_file = tmp_path / "nonexistent.jsonl"
    runner = BenchmarkRunner(benchmark_file=missing_file)

    with pytest.raises(FileNotFoundError) as exc_info:
        runner.run()
    assert "Benchmark file not found" in str(exc_info.value)


def test_benchmark_runner_malformed_json_raises(tmp_path: Path) -> None:
    """BenchmarkRunner raises ValueError when encountering invalid JSON or bad schema."""
    bad_file = tmp_path / "corrupt.jsonl"
    bad_file.write_text('{"sample_id": "incomplete"}\n', encoding="utf-8")

    runner = BenchmarkRunner(benchmark_file=bad_file)
    with pytest.raises(ValueError) as exc_info:
        runner.run()
    assert "Malformed sample at line 1" in str(exc_info.value)


def test_benchmark_runner_execution_with_dataset(tmp_path: Path) -> None:
    """BenchmarkRunner iterates JSONL, resolves image files, and returns summary."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    # Create dummy images
    img1_bytes = _make_test_jpeg_bytes(size=(64, 64), color="red")
    img1_path = images_dir / "img1.jpg"
    img1_path.write_bytes(img1_bytes)

    img2_bytes = _make_test_jpeg_bytes(size=(64, 64), color="blue")
    img2_path = images_dir / "img2.jpg"
    img2_path.write_bytes(img2_bytes)

    sample1 = {
        "sample_id": "test-1",
        "image_rel_path": "images/img1.jpg",
        "source_dataset": "synthetic",
        "source_record_id": "syn-01",
        "canonical_category": "Pothole",
        "original_category": "pothole",
        "category_confidence": 1.0,
        "bounding_boxes": [],
        "text_description": "Damaged asphalt with a deep road pothole",
        "split": "benchmark",
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": "Synthetic test",
        "is_blurry": False,
        "is_low_res": False,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "phash": "1001100110011001",
        "duplicate_group_id": None,
        "review_status": "CONFIRMED",
        "metadata_json": {},
    }

    sample2 = {
        "sample_id": "test-2",
        "image_rel_path": "images/img2.jpg",
        "source_dataset": "synthetic",
        "source_record_id": "syn-02",
        "canonical_category": "Garbage",
        "original_category": "trash",
        "category_confidence": 1.0,
        "bounding_boxes": [],
        "text_description": "Overflowing garbage dump on roadside",
        "split": "benchmark",
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": "Synthetic test",
        "is_blurry": False,
        "is_low_res": False,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "phash": "1001100110011002",
        "duplicate_group_id": None,
        "review_status": "CONFIRMED",
        "metadata_json": {},
    }

    benchmark_jsonl = tmp_path / "benchmark_dataset.jsonl"
    with open(benchmark_jsonl, "w", encoding="utf-8") as f:
        f.write(json.dumps(sample1) + "\n")
        f.write(json.dumps(sample2) + "\n")

    runner = BenchmarkRunner(
        benchmark_file=benchmark_jsonl,
        benchmark_root=tmp_path,
    )

    report = runner.run()

    assert report["total_evaluated"] == 2
    assert "metrics" in report
    assert "latency" in report
    assert len(report["results"]) == 2
    assert report["metrics"]["total_samples"] == 2
    assert "Pothole" in report["metrics"]["per_class"]
    assert "Garbage" in report["metrics"]["per_class"]
    assert report["latency"]["p50"] >= 0.0


def test_benchmark_runner_mode_ablation_and_artifact_export(tmp_path: Path) -> None:
    """BenchmarkRunner correctly handles modes and exports all 6 artifact files."""
    img_dir = tmp_path / "images"
    img_dir.mkdir(parents=True)
    img_bytes = _make_test_jpeg_bytes()
    (img_dir / "sample.jpg").write_bytes(img_bytes)

    sample = {
        "sample_id": "test-mode-1",
        "image_rel_path": "images/sample.jpg",
        "source_dataset": "synthetic",
        "source_record_id": "syn-m1",
        "canonical_category": "Pothole",
        "original_category": "pothole",
        "category_confidence": 1.0,
        "bounding_boxes": [],
        "text_description": "Damaged asphalt with a deep road pothole",
        "split": "benchmark",
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": "Synthetic test",
        "is_blurry": False,
        "is_low_res": False,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "phash": "1001100110011001",
        "duplicate_group_id": None,
        "review_status": "CONFIRMED",
        "metadata_json": {},
    }
    b_file = tmp_path / "benchmark.jsonl"
    b_file.write_text(json.dumps(sample) + "\n", encoding="utf-8")

    out_dir = tmp_path / "runs" / "test_run"
    runner = BenchmarkRunner(benchmark_file=b_file, benchmark_root=tmp_path)

    # 1. Multimodal mode with export
    res_mm = runner.run(mode="multimodal", output_dir=out_dir)
    assert res_mm["total_evaluated"] == 1
    assert res_mm["results"][0]["evaluation_mode"] == "MULTIMODAL"

    # Verify all 6 files exported
    assert (out_dir / "predictions.jsonl").exists()
    assert (out_dir / "metrics.json").exists()
    assert (out_dir / "confusion_matrix.json").exists()
    assert (out_dir / "latency.json").exists()
    assert (out_dir / "failures.jsonl").exists()
    assert (out_dir / "run_metadata.json").exists()

    cm_data = json.loads((out_dir / "confusion_matrix.json").read_text(encoding="utf-8"))
    assert cm_data["total_samples"] == 1
    assert cm_data["matrix_sum"] == 1

    # 2. Vision-only mode
    res_vo = runner.run(mode="vision_only")
    assert res_vo["results"][0]["evaluation_mode"] == "VISION_ONLY"
    assert res_vo["results"][0]["predicted_category"] == "Other"

    # 3. Text-only mode
    res_to = runner.run(mode="text_only")
    assert res_to["results"][0]["evaluation_mode"] == "TEXT_ONLY"
    assert res_to["results"][0]["review_required"] is True


def test_classify_failure_type_heuristics() -> None:
    """classify_failure_type accurately identifies distinct failure causes."""
    from app.evaluation.metrics import classify_failure_type

    # Pipeline error priority
    assert classify_failure_type(
        ground_truth_category="Pothole",
        predicted_category="Other",
        pipeline_errors=["VISION_RUNTIME_ERROR"],
    ) == "PIPELINE_ERROR"

    # Low visual signal
    assert classify_failure_type(
        ground_truth_category="Pothole",
        predicted_category="Other",
        is_blurry=True,
    ) == "LOW_VISUAL_SIGNAL"

    # Text vision conflict
    assert classify_failure_type(
        ground_truth_category="Pothole",
        predicted_category="Road Damage",
        evidence_agreement=0.2,
    ) == "TEXT_VISION_CONFLICT"

    # Misleading text (ground truth keyword absent)
    assert classify_failure_type(
        ground_truth_category="Pothole",
        predicted_category="Road Damage",
        text_description="Deep road cavity and asphalt damage",
    ) == "MISLEADING_TEXT"

    # Category confusion (ground truth keyword present, but ambiguous)
    assert classify_failure_type(
        ground_truth_category="Pothole",
        predicted_category="Road Damage",
        text_description="Deep pothole with asphalt road damage",
    ) == "CATEGORY_CONFUSION"

    # Insufficient context
    assert classify_failure_type(
        ground_truth_category="Road Damage",
        predicted_category="Other",
        text_description="Route de Thonon",
    ) == "INSUFFICIENT_CONTEXT"


def test_frozen_benchmark_v1_full_evaluation() -> None:
    """Validate full 300-sample benchmark execution and invariant properties."""
    benchmark_file = (
        Path(__file__).resolve().parents[3]
        / "datasets"
        / "benchmark_v1"
        / "benchmark_dataset.jsonl"
    )
    if not benchmark_file.exists():
        pytest.skip("Benchmark v1 dataset file not present in repository.")

    benchmark_root = benchmark_file.parent
    runner = BenchmarkRunner(benchmark_file=benchmark_file, benchmark_root=benchmark_root)
    results = runner.run(mode="multimodal")

    assert results["total_evaluated"] == 300
    metrics = results["metrics"]
    assert metrics["total_samples"] == 300
    assert metrics["accuracy"] == 0.79
    assert metrics["macro_f1"] == 0.7934

    # Verify per-class support is exactly 50 for all 6 canonical categories
    per_class = metrics["per_class"]
    for cat in CANONICAL_BENCHMARK_CATEGORIES:
        assert cat in per_class
        assert per_class[cat]["support"] == 50

    # Invariant: Confusion matrix sum strictly equals 300
    cm_matrix = metrics["confusion_matrix"]["matrix"]
    assert sum(sum(row) for row in cm_matrix) == 300


