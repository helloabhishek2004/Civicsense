import base64
import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.core.errors import (
    CorruptImageError,
    ImageDecompressionBombError,
    ImageDimensionsInvalidError,
    InvalidImagePayloadError,
    OversizedImageError,
    TextValidationError,
    UnsupportedImageTypeError,
)
from app.models.enums import PriorityLevel, SeverityLevel
from app.schemas.normalized_prediction import (
    NormalizedPrediction,
    PredictionConfidenceTier,
)
from app.services.ai.decision_engine import PrototypeDecisionEngine
from app.services.ai.fusion_engine import PrototypeFusionEngine
from app.services.ai.input_validator import InputValidator
from app.services.ai.normalized_prediction import PredictionNormalizer
from app.services.ai.vision_analyzer import PrototypeVisionAnalyzer


def _make_test_image_bytes(
    fmt: str = "JPEG",
    size: tuple[int, int] = (100, 100),
    color: str = "blue",
    mode: str = "RGB",
) -> bytes:
    buf = io.BytesIO()
    img = Image.new(mode, size, color=color)
    img.save(buf, format=fmt)
    return buf.getvalue()


def _make_test_image_b64(
    fmt: str = "JPEG",
    size: tuple[int, int] = (100, 100),
    color: str = "blue",
) -> str:
    raw = _make_test_image_bytes(fmt=fmt, size=size, color=color)
    return base64.b64encode(raw).decode("ascii")


# ===========================================================================
# 1. INPUT VALIDATION TESTS (1 to 16)
# ===========================================================================


def test_1_valid_jpeg_image_validation() -> None:
    """Valid JPEG image -> accepted, dimensions/format extracted correctly."""
    data = _make_test_image_bytes("JPEG", (128, 128))
    result = InputValidator.validate_image_bytes(data)
    assert result.mime_type == "image/jpeg"
    assert result.file_extension == ".jpg"
    assert result.width == 128
    assert result.height == 128
    assert result.total_pixels == 128 * 128
    assert len(result.sha256) == 64


def test_2_valid_png_image_validation() -> None:
    """Valid PNG image -> accepted, dimensions/format extracted correctly."""
    data = _make_test_image_bytes("PNG", (200, 150), color="green", mode="RGBA")
    result = InputValidator.validate_image_bytes(data)
    assert result.mime_type == "image/png"
    assert result.file_extension == ".png"
    assert result.width == 200
    assert result.height == 150
    assert result.total_pixels == 30000


def test_3_valid_webp_image_validation() -> None:
    """Valid WebP image -> accepted, dimensions/format extracted correctly."""
    data = _make_test_image_bytes("WEBP", (160, 120))
    result = InputValidator.validate_image_bytes(data)
    assert result.mime_type == "image/webp"
    assert result.file_extension == ".webp"
    assert result.width == 160
    assert result.height == 120


def test_4_corrupt_image_bytes_rejected() -> None:
    """Corrupt image bytes (e.g. truncated JPEG header, random noise) -> rejected with CorruptImageError."""
    # Truncated JPEG signature followed by garbage bytes
    corrupt_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 20 + b"corrupt_random_noise_12345"
    with pytest.raises(CorruptImageError):
        InputValidator.validate_image_bytes(corrupt_bytes)


def test_5_declared_jpeg_actual_png_magic_bytes() -> None:
    """Declared JPEG but actual PNG magic bytes -> correctly identified as PNG (magic bytes take precedence)."""
    png_bytes = _make_test_image_bytes("PNG", (100, 100))
    result = InputValidator.validate_image_bytes(png_bytes, declared_mime_type="image/jpeg")
    assert result.mime_type == "image/png"
    assert result.file_extension == ".png"


def test_6_below_minimum_dimensions_rejected() -> None:
    """Below-minimum dimensions (e.g. 16x16 px) -> rejected with ImageDimensionsInvalidError."""
    data = _make_test_image_bytes("PNG", (16, 16))
    with pytest.raises(ImageDimensionsInvalidError) as exc_info:
        InputValidator.validate_image_bytes(data)
    assert "violate acceptable bounds" in str(exc_info.value.message)


def test_7_above_maximum_dimensions_rejected() -> None:
    """Above-maximum dimensions (e.g. 9000x1000 px > 8192px max dim) -> rejected with ImageDimensionsInvalidError."""
    # 9000 x 1000 = 9,000,000 pixels (below 25M pixel bomb limit, but width 9000 > 8192 max dim)
    buf = io.BytesIO()
    img = Image.new("1", (9000, 1000), 0)
    img.save(buf, format="PNG")
    with pytest.raises(ImageDimensionsInvalidError) as exc_info:
        InputValidator.validate_image_bytes(buf.getvalue())
    assert "violate acceptable bounds" in str(exc_info.value.message)


def test_8_image_payload_exceeding_max_byte_size_rejected() -> None:
    """Image payload exceeding max byte size (e.g. >10MB) -> rejected with OversizedImageError."""
    settings = get_settings()
    oversized_bytes = b"\xff\xd8\xff" + b"\x00" * (settings.MAX_IMAGE_SIZE_BYTES + 1024)
    with pytest.raises(OversizedImageError) as exc_info:
        InputValidator.validate_image_bytes(oversized_bytes)
    assert "exceeds maximum allowed limit" in str(exc_info.value.message)


def test_9_decompression_bomb_attempt_rejected() -> None:
    """Decompression bomb attempt (e.g. 5200x5200 > 25 megapixels) -> rejected with ImageDecompressionBombError."""
    # 5200 x 5200 = 27,040,000 pixels (> 25,000,000 max pixels limit)
    # Compressed 1-bit PNG is only ~3 KB, but decompresses into 27M pixels
    buf = io.BytesIO()
    img = Image.new("1", (5200, 5200), 0)
    img.save(buf, format="PNG")
    raw_bomb_bytes = buf.getvalue()

    with pytest.raises(ImageDecompressionBombError) as exc_info:
        InputValidator.validate_image_bytes(raw_bomb_bytes)
    assert "IMAGE_DECOMPRESSION_BOMB" == exc_info.value.code


def test_10_empty_image_payload_rejected() -> None:
    """Empty image payload (0 bytes) -> rejected with InvalidImagePayloadError."""
    with pytest.raises(InvalidImagePayloadError):
        InputValidator.validate_image_bytes(b"")


def test_11_unsupported_image_formats_rejected() -> None:
    """Unsupported image formats (GIF, SVG, BMP, Executable disguised as image) -> rejected with UnsupportedImageTypeError."""
    # GIF format
    gif_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    with pytest.raises(UnsupportedImageTypeError):
        InputValidator.validate_image_bytes(gif_bytes)

    # SVG format
    svg_bytes = b"<?xml version='1.0'?><svg xmlns='http://www.w3.org/2000/svg'></svg>"
    with pytest.raises(UnsupportedImageTypeError):
        InputValidator.validate_image_bytes(svg_bytes)

    # Executable disguised as image
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00"
    with pytest.raises(UnsupportedImageTypeError):
        InputValidator.validate_image_bytes(exe_bytes)


def test_12_valid_text_description_normalized() -> None:
    """Valid text description within limits -> accepted, sanitized, NFKC normalized."""
    # Fullwidth characters like Ｐｏｔｈｏｌｅ should normalize to ASCII Pothole
    raw_text = "Ｐｏｔｈｏｌｅ on 8th Cross Road causing traffic congestion."
    res = InputValidator.validate_and_sanitize_text(raw_text)
    assert res.cleaned_text.startswith("Pothole on 8th Cross")
    assert res.character_count > 10
    assert res.word_count >= 5


def test_13_text_with_null_and_control_chars_sanitized() -> None:
    """Text description with null bytes or control characters -> sanitized/stripped cleanly."""
    raw_text = "Deep road cavity\x00\x01\x08 near junction\x1b[31m dangerous\x07."
    res = InputValidator.validate_and_sanitize_text(raw_text)
    assert "\x00" not in res.cleaned_text
    assert "\x01" not in res.cleaned_text
    assert "\x08" not in res.cleaned_text
    assert "Deep road cavity near junction" in res.cleaned_text


def test_14_text_exceeding_max_character_limit_rejected() -> None:
    """Text description exceeding max character limit -> rejected with TextValidationError."""
    settings = get_settings()
    oversized_text = "Severe road defect. " * (settings.MAX_DESCRIPTION_LENGTH // 15 + 10)
    with pytest.raises(TextValidationError) as exc_info:
        InputValidator.validate_and_sanitize_text(oversized_text)
    assert "exceeds maximum limit" in str(exc_info.value.message)


def test_15_text_degenerative_repeated_characters_handled() -> None:
    """Text description with degenerative repeated-character runs (e.g. 'aaaaa...' * 500) -> handled cleanly."""
    repetitive_text = "Help road is broken " + ("a" * 250)
    with pytest.raises(TextValidationError) as exc_info:
        InputValidator.validate_and_sanitize_text(repetitive_text)
    assert "repeated character run" in str(exc_info.value.message)


def test_16_empty_or_whitespace_text_rejected() -> None:
    """Empty or whitespace-only description -> rejected with clear validation error."""
    with pytest.raises(TextValidationError):
        InputValidator.validate_and_sanitize_text("")

    with pytest.raises(TextValidationError):
        InputValidator.validate_and_sanitize_text("   \n\t   ")


# ===========================================================================
# 2. PIPELINE RESILIENCE & FALLBACK TESTS (17 to 21)
# ===========================================================================


def test_17_multimodal_pipeline_execution(client: TestClient) -> None:
    """Report with valid text and valid image -> full multimodal pipeline executes, both modalities contribute."""
    img_b64 = _make_test_image_b64("JPEG", (100, 100))
    payload = {
        "location": {"latitude": 12.9716, "longitude": 77.5946, "address_hint": "MG Road"},
        "description": "Massive pothole crater on the road causing major hazard",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "pothole_crater.jpg",
                "data_base64": img_b64,
                "mime_type": "image/jpeg",
                "metadata_json": {"prototype_category": "Pothole"},
            }
        ],
    }
    r = client.post("/api/v1/reports", json=payload)
    assert r.status_code == 201
    report_id = r.json()["id"]

    # Process AI
    ai_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert ai_res.status_code == 202
    job_data = ai_res.json()
    assert job_data["status"] == "COMPLETED"

    ai_get = client.get(f"/api/v1/reports/{report_id}/ai")
    assert ai_get.status_code == 200
    ai_data = ai_get.json()
    analysis = ai_data["ai_analysis"]
    assert analysis["predicted_category"] == "Pothole"
    assert analysis["confidence"] >= 0.70
    assert analysis["normalized_prediction"]["inference_source"] == "server_rule_engine"
    assert analysis["normalized_prediction"]["hardware_acceleration"] == "NONE"


def test_18_unimodal_fallback_missing_image(client: TestClient) -> None:
    """Report with valid text but missing image -> unimodal fallback executes, confidence penalized, review_required=True."""
    payload = {
        "location": {"latitude": 12.9716, "longitude": 77.5946, "address_hint": "Brigade Road"},
        "description": "Large accumulation of garbage and waste dump on pavement",
        "evidence": [],  # No image attached
    }
    r = client.post("/api/v1/reports", json=payload)
    assert r.status_code == 201
    report_id = r.json()["id"]

    ai_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert ai_res.status_code == 202
    job_data = ai_res.json()
    assert job_data["status"] == "COMPLETED"
    assert job_data["review_required"] is True
    assert job_data["review_reason"] == "UNIMODAL_TEXT_FALLBACK"

    ai_get = client.get(f"/api/v1/reports/{report_id}/ai")
    ai_data = ai_get.json()
    norm_pred = ai_data["ai_analysis"]["normalized_prediction"]
    assert norm_pred["inference_source"] == "unimodal_text_fallback"
    assert norm_pred["requires_review"] is True
    assert "IMAGE_UNAVAILABLE_FALLBACK" in norm_pred["warnings"]


def test_19_unimodal_fallback_corrupt_image(client: TestClient) -> None:
    """Report with valid text but corrupt image -> unimodal fallback executes, pipeline completes (no crash), review_required=True."""
    # Provide corrupted base64 data for image
    corrupt_b64 = base64.b64encode(b"\xff\xd8\xff\xe0garbage_random_corrupt_bytes").decode("ascii")
    payload = {
        "location": {"latitude": 12.9716, "longitude": 77.5946},
        "description": "Severe road fissure and asphalt cracking",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "crack_corrupted.jpg",
                "data_base64": corrupt_b64,
                "mime_type": "image/jpeg",
            }
        ],
    }
    r = client.post("/api/v1/reports", json=payload)
    assert r.status_code == 201
    report_id = r.json()["id"]

    ai_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert ai_res.status_code == 202
    job_data = ai_res.json()
    # Does not crash! Completes with degraded unimodal fallback
    assert job_data["status"] == "COMPLETED"
    assert job_data["review_required"] is True

    ai_get = client.get(f"/api/v1/reports/{report_id}/ai")
    ai_data = ai_get.json()
    assert ai_data["ai_analysis"]["review_required"] is True
    norm_pred = ai_data["ai_analysis"]["normalized_prediction"]
    assert norm_pred["inference_source"] == "unimodal_text_fallback"


def test_20_processor_exception_in_vision_stage_graceful(client: TestClient) -> None:
    """Processor exception in vision stage -> caught gracefully, recorded in event audit trail, report transitions safely without data loss."""
    payload = {
        "location": {"latitude": 12.9716, "longitude": 77.5946},
        "description": "Streetlight luminaire defective and dark at night",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "streetlight.jpg",
                "mime_type": "image/jpeg",
            }
        ],
    }
    r = client.post("/api/v1/reports", json=payload)
    assert r.status_code == 201
    report_id = r.json()["id"]

    # Simulate an unexpected exception in vision analyzer
    with patch.object(
        PrototypeVisionAnalyzer,
        "analyze",
        side_effect=RuntimeError("Simulated GPU/Vision hardware fault"),
    ):
        ai_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
        assert ai_res.status_code == 202
        job_data = ai_res.json()
        assert job_data["status"] == "COMPLETED"
        assert job_data["review_required"] is True

    # Check event trail
    events_res = client.get(f"/api/v1/reports/{report_id}/ai/events")
    events = events_res.json()
    stages = [ev["stage"] for ev in events]
    assert "VISION_ANALYSIS" in stages
    assert "TEXT_ANALYSIS" in stages
    assert "HUMAN_REVIEW" in stages


def test_21_malformed_model_output_rejected_and_fallback_applied() -> None:
    """Malformed model output (missing keys, out-of-range confidence) -> rejected by normalizer with schema validation error, fallback applied."""
    # 1. Missing confidence
    with pytest.raises(ValueError) as exc:
        PredictionNormalizer.normalize(
            raw_vision={},
            raw_text={},
            raw_fusion={},
            raw_decision={"suggested_category": "Pothole"},  # Missing confidence
            inference_time_ms=10,
        )
    assert "missing 'confidence' key" in str(exc.value)

    # 2. Out-of-bounds confidence (1.50)
    with pytest.raises(ValueError) as exc:
        PredictionNormalizer.normalize(
            raw_vision={},
            raw_text={},
            raw_fusion={},
            raw_decision={"suggested_category": "Pothole", "confidence": 1.50},
            inference_time_ms=10,
        )
    assert "outside allowable range" in str(exc.value)

    # 3. Safe fallback prediction can be created
    fallback = PredictionNormalizer.create_fallback_prediction("Test malformed output")
    assert fallback.predicted_category == "Other"
    assert fallback.confidence == 0.0
    assert fallback.confidence_tier == PredictionConfidenceTier.FAILED
    assert fallback.requires_review is True


# ===========================================================================
# 3. CONFIDENCE & DECISION GATE TESTS (22 to 27)
# ===========================================================================


def test_22_high_confidence_tier_no_review() -> None:
    """High confidence prediction (>= 0.80) with matching modalities -> review_required=False, confidence_tier='HIGH'."""
    raw_decision = {
        "suggested_category": "Pothole",
        "suggested_severity": SeverityLevel.HIGH,
        "operational_priority": PriorityLevel.HIGH,
        "confidence": 0.85,
        "review_required": False,
        "review_reason": None,
        "decision_explanation": "Concordant multimodal signals.",
    }
    raw_fusion = {"modality_agreement": 0.90}
    norm = PredictionNormalizer.normalize(
        raw_vision={"has_image": True, "predicted_category": "Pothole"},
        raw_text={"predicted_category": "Pothole"},
        raw_fusion=raw_fusion,
        raw_decision=raw_decision,
        inference_time_ms=15,
    )
    assert norm.confidence_tier == PredictionConfidenceTier.HIGH
    assert norm.requires_review is False
    assert norm.confidence == 0.85


def test_23_medium_confidence_tier() -> None:
    """Medium confidence prediction (0.65 - 0.79) -> confidence_tier='MEDIUM'."""
    raw_decision = {
        "suggested_category": "Garbage",
        "suggested_severity": SeverityLevel.MEDIUM,
        "operational_priority": PriorityLevel.MEDIUM,
        "confidence": 0.72,
        "review_required": False,
        "review_reason": None,
        "decision_explanation": "Acceptable confidence.",
    }
    raw_fusion = {"modality_agreement": 0.75}
    norm = PredictionNormalizer.normalize(
        raw_vision={"has_image": True, "predicted_category": "Garbage"},
        raw_text={"predicted_category": "Garbage"},
        raw_fusion=raw_fusion,
        raw_decision=raw_decision,
        inference_time_ms=20,
    )
    assert norm.confidence_tier == PredictionConfidenceTier.MEDIUM


def test_24_low_confidence_tier_requires_review() -> None:
    """Low confidence prediction (0.50 - 0.64) -> review_required=True, review_reason contains 'LOW_CONFIDENCE', confidence_tier='LOW'."""
    engine = PrototypeDecisionEngine()
    vision_res = {
        "has_image": True,
        "predicted_category": "Other",
        "confidence": 0.50,
        "predicted_severity": SeverityLevel.LOW,
    }
    text_res = {
        "predicted_category": "Other",
        "confidence": 0.55,
        "predicted_severity": SeverityLevel.LOW,
    }
    fusion_res = {"modality_agreement": 0.50}

    decision = engine.decide(vision_res, text_res, fusion_res)
    assert decision["review_required"] is True
    assert "LOW_CONFIDENCE" in (decision["review_reason"] or "")

    norm = PredictionNormalizer.normalize(
        raw_vision=vision_res,
        raw_text=text_res,
        raw_fusion=fusion_res,
        raw_decision=decision,
        inference_time_ms=10,
    )
    assert norm.requires_review is True


def test_25_uncertain_confidence_tier() -> None:
    """Uncertain prediction (< 0.50) -> review_required=True, confidence_tier='UNCERTAIN'."""
    raw_decision = {
        "suggested_category": "Pothole",
        "suggested_severity": SeverityLevel.LOW,
        "operational_priority": PriorityLevel.LOW,
        "confidence": 0.42,
        "review_required": True,
        "review_reason": "LOW_CONFIDENCE",
        "decision_explanation": "Low confidence signal.",
    }
    norm = PredictionNormalizer.normalize(
        raw_vision={"has_image": True},
        raw_text={},
        raw_fusion={"modality_agreement": 0.40},
        raw_decision=raw_decision,
        inference_time_ms=12,
    )
    assert norm.confidence_tier == PredictionConfidenceTier.UNCERTAIN
    assert norm.requires_review is True


def test_26_conflicting_modalities_requires_review() -> None:
    """Conflicting modalities (vision says Pothole, text says Garbage, agreement < 0.60) -> review_required=True, review_reason contains 'MODALITY_DISAGREEMENT'."""
    engine = PrototypeDecisionEngine()
    vision_res = {
        "has_image": True,
        "predicted_category": "Pothole",
        "confidence": 0.85,
        "predicted_severity": SeverityLevel.HIGH,
    }
    text_res = {
        "predicted_category": "Garbage",
        "confidence": 0.80,
        "predicted_severity": SeverityLevel.LOW,
    }
    # Modality mismatch
    fusion_engine = PrototypeFusionEngine()
    fusion_res = fusion_engine.fuse(vision_res, text_res)
    assert fusion_res["modality_agreement"] < 0.60

    decision = engine.decide(vision_res, text_res, fusion_res)
    assert decision["review_required"] is True
    assert "DISAGREEMENT" in (decision["review_reason"] or "")


def test_27_category_other_requires_review() -> None:
    """Category 'Other' prediction -> review_required=True, review_reason contains 'UNCLASSIFIED_ISSUE'."""
    engine = PrototypeDecisionEngine()
    vision_res = {
        "has_image": True,
        "predicted_category": "Other",
        "confidence": 0.80,
        "predicted_severity": SeverityLevel.LOW,
    }
    text_res = {
        "predicted_category": "Other",
        "confidence": 0.80,
        "predicted_severity": SeverityLevel.LOW,
    }
    fusion_res = {"modality_agreement": 0.90}

    decision = engine.decide(vision_res, text_res, fusion_res)
    assert decision["suggested_category"] == "Other"
    assert decision["review_required"] is True
    assert "UNCLASSIFIED_ISSUE" in (decision["review_reason"] or "")


# ===========================================================================
# 4. ADAPTER & NORMALIZATION TESTS (28 to 30)
# ===========================================================================


def test_28_raw_model_dict_normalized_to_schema() -> None:
    """Raw model dictionary input -> normalized into valid NormalizedPrediction instance matching Pydantic schema."""
    raw_decision = {
        "suggested_category": "Water Leakage",
        "suggested_severity": SeverityLevel.HIGH,
        "operational_priority": PriorityLevel.HIGH,
        "confidence": 0.82,
        "review_required": False,
        "review_reason": None,
        "decision_explanation": "High confidence fluid leak detection.",
    }
    raw_vision = {"has_image": True, "predicted_category": "Water Leakage", "confidence": 0.80}
    raw_text = {"predicted_category": "Water Leakage", "confidence": 0.85}
    raw_fusion = {"modality_agreement": 0.88}

    norm = PredictionNormalizer.normalize(
        raw_vision=raw_vision,
        raw_text=raw_text,
        raw_fusion=raw_fusion,
        raw_decision=raw_decision,
        inference_time_ms=25,
        model_name="test_model",
        model_version="1.0.0",
        timing_breakdown={"total_pipeline_ms": 25},
    )

    assert isinstance(norm, NormalizedPrediction)
    assert norm.predicted_category == "Water Leakage"
    assert norm.category_label == "Water Pipeline Leak & Fluid Pooling"
    assert norm.confidence == 0.82
    assert norm.confidence_tier == PredictionConfidenceTier.HIGH
    assert norm.severity == SeverityLevel.HIGH
    assert norm.priority == PriorityLevel.HIGH
    assert norm.model_name == "test_model"
    assert norm.inference_time_ms == 25
    assert norm.hardware_acceleration == "NONE"
    assert "AI predictions are advisory suggestions" in norm.disclaimer


def test_29_verification_separation_invariant(client: TestClient) -> None:
    """Verification separation invariant: AI output contains disclaimer, does not set official report verification status."""
    payload = {
        "location": {"latitude": 12.9716, "longitude": 77.5946},
        "description": "Clogged storm water drainage overflowing onto sidewalk",
        "evidence": [],
    }
    r = client.post("/api/v1/reports", json=payload)
    report_id = r.json()["id"]

    # Run AI processing
    client.post(f"/api/v1/reports/{report_id}/ai/process")

    # Fetch AI result and report details
    ai_res = client.get(f"/api/v1/reports/{report_id}/ai")
    ai_data = ai_res.json()

    # Invariant 1: Advisory disclaimer is strictly present
    assert "disclaimer" in ai_data["ai_analysis"]["analysis_metadata"]
    disclaimer = ai_data["ai_analysis"]["analysis_metadata"]["disclaimer"]
    assert (
        "do not constitute official municipal verification" in disclaimer.lower()
        or "not a deep learning model" in disclaimer.lower()
    )

    # Invariant 2: Official human verification remains None / Unverified
    assert ai_data["verification"] is None

    # Invariant 3: Official report status is VERIFICATION_REQUIRED or AI_PROCESSED, never VERIFIED
    report_res = client.get(f"/api/v1/reports/{report_id}")
    report_status = report_res.json()["status"]
    assert report_status != "VERIFIED"
    assert report_status in ("VERIFICATION_REQUIRED", "AI_PROCESSED")


def test_30_end_to_end_api_pipeline_hardening(client: TestClient) -> None:
    """End-to-end API integration: POST /api/v1/reports followed by POST /api/v1/reports/{id}/ai/process returns hardened response with telemetry."""
    img_b64 = _make_test_image_b64("WEBP", (150, 150))
    payload = {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address_hint": "Indiranagar 100 Feet Road",
        },
        "description": "Deep asphalt pothole cavity creating severe accident hazard",
        "citizen_name": "Anita Rao",
        "citizen_phone": "9876543210",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "pothole_road.webp",
                "data_base64": img_b64,
                "mime_type": "image/webp",
                "metadata_json": {"prototype_category": "Pothole"},
            }
        ],
    }

    # 1. Ingestion
    create_res = client.post("/api/v1/reports", json=payload)
    assert create_res.status_code == 201
    rep_id = create_res.json()["id"]

    # 2. AI Processing
    process_res = client.post(f"/api/v1/reports/{rep_id}/ai/process")
    assert process_res.status_code == 202
    job = process_res.json()
    assert job["status"] == "COMPLETED"

    # 3. Detailed AI Inspection
    ai_res = client.get(f"/api/v1/reports/{rep_id}/ai")
    assert ai_res.status_code == 200
    res_data = ai_res.json()

    analysis = res_data["ai_analysis"]
    meta = analysis["analysis_metadata"]
    norm = analysis["normalized_prediction"]

    # Telemetry and Timing checks
    assert "timing_breakdown" in meta
    timing = meta["timing_breakdown"]
    assert "intake_validation_ms" in timing
    assert "vision_inference_ms" in timing
    assert "text_inference_ms" in timing
    assert "total_pipeline_ms" in timing

    # Hardware transparency check
    assert meta["hardware_acceleration"] == "NONE"
    assert norm["hardware_acceleration"] == "NONE"
    assert "device_metrics" in meta
    assert meta["device_metrics"]["cpu_count"] >= 1

    # Schema integrity check
    assert norm["predicted_category"] == "Pothole"
    assert norm["confidence"] >= 0.70
    assert norm["severity"] in ["HIGH", "MEDIUM", "LOW", "CRITICAL"]
    assert norm["priority"] in ["HIGH", "MEDIUM", "LOW", "CRITICAL"]
    assert len(norm["top_predictions"]) >= 1
