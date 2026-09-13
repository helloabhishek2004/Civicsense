"""CivicSense Unit Tests for Real Vision Model Adapter (Phase 3.4)."""

import io
import tempfile
from pathlib import Path

from PIL import Image

from app.services.ai.real_vision_model import RealVisionModel
from app.services.ai.vision_interface import (
    CANONICAL_VISION_CATEGORIES,
    VisionInferenceOutcome,
    VisionModelStatus,
)

repo_root = Path(__file__).resolve().parents[3]


def _make_dummy_image_bytes(color: tuple[int, int, int] = (100, 150, 200)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (224, 224), color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_real_vision_model_unavailable_when_no_checkpoint() -> None:
    """Without a checkpoint, RealVisionModel reports UNAVAILABLE and rejects predictions."""
    model = RealVisionModel(checkpoint_path=None)
    assert model.status == VisionModelStatus.UNAVAILABLE

    res = model.predict(_make_dummy_image_bytes())
    assert res.outcome == VisionInferenceOutcome.MODEL_UNAVAILABLE
    assert res.predicted_category is None
    assert res.confidence == 0.0
    assert res.requires_review is True


def test_real_vision_model_loading_failed_on_invalid_checkpoint() -> None:
    """A corrupted checkpoint file puts RealVisionModel into LOADING_FAILED state."""
    with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
        tmp.write(b"not a pytorch checkpoint file")
        tmp_name = tmp.name

    try:
        model = RealVisionModel(checkpoint_path=tmp_name)
        assert model.status == VisionModelStatus.LOADING_FAILED
        res = model.predict(_make_dummy_image_bytes())
        assert res.outcome == VisionInferenceOutcome.INFERENCE_ERROR
    finally:
        Path(tmp_name).unlink(missing_ok=True)


def test_real_vision_model_predict_empty_bytes() -> None:
    """Empty image buffer yields PREPROCESSING_ERROR."""
    ckpt_path = repo_root / "models" / "mobilenet_v3_small_v1" / "exp_b" / "exp_b_best.pt"
    if not ckpt_path.exists():
        ckpt_path = repo_root / "models" / "mobilenet_v3_small_v1" / "exp_a" / "exp_a_best.pt"

    model = RealVisionModel(checkpoint_path=ckpt_path)
    assert model.status == VisionModelStatus.READY

    res = model.predict(b"")
    assert res.outcome == VisionInferenceOutcome.PREPROCESSING_ERROR
    assert res.confidence == 0.0
    assert res.requires_review is True


def test_real_vision_model_predict_corrupt_bytes() -> None:
    """Corrupted image bytes yield PREPROCESSING_ERROR."""
    ckpt_path = repo_root / "models" / "mobilenet_v3_small_v1" / "exp_b" / "exp_b_best.pt"
    if not ckpt_path.exists():
        ckpt_path = repo_root / "models" / "mobilenet_v3_small_v1" / "exp_a" / "exp_a_best.pt"

    model = RealVisionModel(checkpoint_path=ckpt_path)
    res = model.predict(b"not a valid image format bytes")
    assert res.outcome == VisionInferenceOutcome.PREPROCESSING_ERROR
    assert res.confidence == 0.0
    assert "preprocessing/decoding failed" in (res.error_message or "")


def test_real_vision_model_predict_success_with_trained_checkpoint() -> None:
    """Trained checkpoint successfully performs inference and outputs calibrated probabilities."""
    ckpt_path = repo_root / "models" / "mobilenet_v3_small_v1" / "exp_b" / "exp_b_best.pt"
    if not ckpt_path.exists():
        ckpt_path = repo_root / "models" / "mobilenet_v3_small_v1" / "exp_a" / "exp_a_best.pt"

    assert ckpt_path.exists(), "Trained checkpoint missing"

    model = RealVisionModel(checkpoint_path=ckpt_path, confidence_threshold=0.60)
    assert model.status == VisionModelStatus.READY

    img_bytes = _make_dummy_image_bytes()
    res = model.predict(img_bytes)

    assert res.outcome in (VisionInferenceOutcome.SUCCESS, VisionInferenceOutcome.LOW_CONFIDENCE)
    assert res.predicted_category in CANONICAL_VISION_CATEGORIES
    assert 0.0 <= res.confidence <= 1.0
    assert len(res.class_probabilities) == 6
    assert abs(sum(res.class_probabilities.values()) - 1.0) < 0.01
    assert res.inference_time_ms > 0.0
    assert res.preprocessing_time_ms >= 0.0
