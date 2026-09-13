"""CivicSense Phase 3.3.1 — Vision Model Interface Unit Tests.

Validates the decoupled visual model interface and strict separation between:
1. Real model prediction of Other
2. Model unavailable
3. Model loading failure
4. Image preprocessing failure
5. Inference failure
6. Low-confidence prediction
Also verifies that benchmark_v1 and baseline_v1 remain completely unmodified.
"""

import hashlib
import io
import json
from pathlib import Path

from PIL import Image

from app.services.ai.vision_interface import (
    CANONICAL_VISION_CATEGORIES,
    MockVisionModel,
    PrototypeVisionModel,
    VisionInferenceOutcome,
    VisionModelMetadata,
    VisionModelStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_DIR = REPO_ROOT / "datasets" / "benchmark_v1"
BASELINE_DIR = REPO_ROOT / "datasets" / "evaluation_runs" / "baseline_v1"


def _make_test_jpeg_bytes(size: tuple[int, int] = (64, 64)) -> bytes:
    """Helper to generate in-memory valid JPEG bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color="blue")
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ===========================================================================
# 1. ENUM & METADATA CONTRACT TESTS
# ===========================================================================


def test_canonical_categories_match_project_spec() -> None:
    """Visual task requires exactly six canonical categories."""
    assert len(CANONICAL_VISION_CATEGORIES) == 6
    assert set(CANONICAL_VISION_CATEGORIES) == {
        "Pothole",
        "Road Damage",
        "Garbage",
        "Water Leakage",
        "Streetlight",
        "Other",
    }


def test_vision_model_metadata_serialization() -> None:
    """VisionModelMetadata serializes cleanly with strict types."""
    meta = VisionModelMetadata(
        model_name="mobilenet_v3_small",
        model_version="1.0.0",
        architecture_family="MobileNet",
        input_resolution=(224, 224),
        num_classes=6,
        device="cpu",
        runtime="pytorch_cpu",
        quantization="int8",
    )
    assert meta.model_name == "mobilenet_v3_small"
    assert meta.num_classes == 6
    assert meta.quantization == "int8"


# ===========================================================================
# 2. STRICT OUTCOME TAXONOMY TESTS (SIX DISTINCT STATES)
# ===========================================================================


def test_outcome_1_real_other_prediction() -> None:
    """A real prediction of 'Other' must have outcome=SUCCESS and predicted_category='Other'."""
    model = MockVisionModel(
        simulated_status=VisionModelStatus.READY,
        forced_outcome=VisionInferenceOutcome.SUCCESS,
        forced_category="Other",
        forced_confidence=0.88,
    )
    pred = model.predict(b"valid-image-bytes")

    assert pred.outcome == VisionInferenceOutcome.SUCCESS
    assert pred.predicted_category == "Other"
    assert pred.confidence == 0.88
    assert pred.error_message is None
    # Real Other requires administrative review per policy
    assert pred.requires_review is True


def test_outcome_2_model_unavailable() -> None:
    """When model is unavailable, outcome must be MODEL_UNAVAILABLE, category must be None, confidence 0.0."""
    model = MockVisionModel(simulated_status=VisionModelStatus.UNAVAILABLE)
    pred = model.predict(b"valid-image-bytes")

    assert pred.outcome == VisionInferenceOutcome.MODEL_UNAVAILABLE
    assert pred.predicted_category is None
    assert pred.confidence == 0.0
    assert pred.error_message is not None
    assert "not ready" in pred.error_message


def test_outcome_3_model_loading_failed() -> None:
    """When model loading fails, outcome must be MODEL_UNAVAILABLE and category must be None."""
    model = MockVisionModel(
        simulated_status=VisionModelStatus.LOADING_FAILED,
        forced_error="Checkpoint checksum corrupted.",
    )
    pred = model.predict(b"valid-image-bytes")

    assert pred.outcome == VisionInferenceOutcome.MODEL_UNAVAILABLE
    assert pred.predicted_category is None
    assert pred.confidence == 0.0
    assert pred.error_message == "Checkpoint checksum corrupted."


def test_outcome_4_preprocessing_failure() -> None:
    """Preprocessing failure must report PREPROCESSING_ERROR and not masquerade as 'Other'."""
    model = MockVisionModel(
        forced_outcome=VisionInferenceOutcome.PREPROCESSING_ERROR,
        forced_error="Corrupt JPEG bitstream header.",
    )
    pred = model.predict(b"bad-bytes")

    assert pred.outcome == VisionInferenceOutcome.PREPROCESSING_ERROR
    assert pred.predicted_category is None
    assert pred.confidence == 0.0
    assert pred.error_message == "Corrupt JPEG bitstream header."


def test_outcome_5_inference_failure() -> None:
    """Runtime inference crash must report INFERENCE_ERROR and not masquerade as 'Other'."""
    model = MockVisionModel(
        forced_outcome=VisionInferenceOutcome.INFERENCE_ERROR,
        forced_error="RuntimeError: CUDA/CPU tensor shape mismatch.",
    )
    pred = model.predict(b"valid-bytes")

    assert pred.outcome == VisionInferenceOutcome.INFERENCE_ERROR
    assert pred.predicted_category is None
    assert pred.confidence == 0.0
    assert "shape mismatch" in (pred.error_message or "")


def test_outcome_6_low_confidence_prediction() -> None:
    """Low-confidence inference preserves the candidate category but sets LOW_CONFIDENCE outcome."""
    model = MockVisionModel(
        forced_outcome=VisionInferenceOutcome.LOW_CONFIDENCE,
        forced_category="Pothole",
        forced_confidence=0.42,
    )
    pred = model.predict(b"valid-bytes")

    assert pred.outcome == VisionInferenceOutcome.LOW_CONFIDENCE
    assert pred.predicted_category == "Pothole"
    assert pred.confidence == 0.42
    assert pred.requires_review is True


# ===========================================================================
# 3. PROTOTYPE VISION MODEL ADAPTER TESTS
# ===========================================================================


def test_prototype_vision_model_predict_clean_image() -> None:
    """PrototypeVisionModel correctly evaluates valid JPEG bytes."""
    model = PrototypeVisionModel(confidence_threshold=0.70)
    assert model.status == VisionModelStatus.READY
    assert model.metadata.model_name == "prototype_vision_analyzer"

    img_bytes = _make_test_jpeg_bytes()
    pred = model.predict(img_bytes)

    # 0.50 confidence is below 0.70 threshold, so outcome is LOW_CONFIDENCE
    assert pred.outcome == VisionInferenceOutcome.LOW_CONFIDENCE
    assert pred.predicted_category == "Other"
    assert pred.confidence == 0.50
    assert pred.requires_review is True
    assert "Other" in pred.class_probabilities
    assert pred.class_probabilities["Other"] == 0.50


def test_prototype_vision_model_predict_corrupt_and_empty_image() -> None:
    """PrototypeVisionModel flags corrupted and empty bytes as PREPROCESSING_ERROR."""
    model = PrototypeVisionModel()

    # Empty bytes
    pred_empty = model.predict(b"")
    assert pred_empty.outcome == VisionInferenceOutcome.PREPROCESSING_ERROR
    assert pred_empty.predicted_category is None
    assert pred_empty.confidence == 0.0

    # Corrupt bytes
    pred_corrupt = model.predict(b"not-a-valid-jpeg-stream")
    assert pred_corrupt.outcome == VisionInferenceOutcome.PREPROCESSING_ERROR
    assert pred_corrupt.predicted_category is None
    assert pred_corrupt.confidence == 0.0


def test_vision_model_batch_prediction() -> None:
    """VisionModel.predict_batch evaluates lists of image bytes sequentially."""
    model = MockVisionModel(forced_category="Streetlight", forced_confidence=0.91)
    batch = [_make_test_jpeg_bytes(), _make_test_jpeg_bytes()]
    preds = model.predict_batch(batch)

    assert len(preds) == 2
    for p in preds:
        assert p.predicted_category == "Streetlight"
        assert p.confidence == 0.91


# ===========================================================================
# 4. BENCHMARK & BASELINE IMMUTABILITY INVARIANTS
# ===========================================================================


def test_benchmark_frozen_manifest_invariant() -> None:
    """Frozen benchmark dataset and manifest must remain strictly unmodified."""
    manifest_path = BENCHMARK_DIR / "manifest.json"
    dataset_path = BENCHMARK_DIR / "benchmark_dataset.jsonl"

    assert manifest_path.is_file()
    assert dataset_path.is_file()

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    hasher = hashlib.sha256()
    with open(dataset_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)

    computed_hash = hasher.hexdigest()
    assert manifest.get("integrity_hash") == computed_hash
    assert manifest.get("total_sample_count") == 300


def test_official_baseline_invariant() -> None:
    """Official baseline run metrics must remain strictly preserved."""
    metrics_path = BASELINE_DIR / "metrics.json"
    assert metrics_path.is_file()

    with open(metrics_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["classification"]["total_samples"] == 300
    assert data["classification"]["accuracy"] == 0.79
