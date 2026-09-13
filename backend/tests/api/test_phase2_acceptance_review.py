import base64
import io
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.errors import TextValidationError
from app.services.ai.input_validator import InputValidator


def _make_test_image_b64(fmt: str = "JPEG", size: tuple[int, int] = (128, 128)) -> str:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(100, 150, 200))
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ===========================================================================
# 1. TEXT VALIDATION REVIEW REGRESSIONS
# ===========================================================================


def test_text_validation_short_meaningful_tokens_accepted() -> None:
    """Short meaningful civic signal descriptions (>= 3 chars) are accepted,
    while < 3 chars or whitespace are rejected.
    """
    # 3 and 4 character words must be accepted
    res_sos = InputValidator.validate_and_sanitize_text("SOS")
    assert res_sos.cleaned_text == "SOS"
    assert "SHORT_DESCRIPTION_ACCEPTED" in res_sos.warnings

    res_leak = InputValidator.validate_and_sanitize_text("Leak")
    assert res_leak.cleaned_text == "Leak"
    assert "SHORT_DESCRIPTION_ACCEPTED" in res_leak.warnings

    res_fire = InputValidator.validate_and_sanitize_text("Fire")
    assert res_fire.cleaned_text == "Fire"
    assert "SHORT_DESCRIPTION_ACCEPTED" in res_fire.warnings

    # Sub-3 character strings are rejected
    with pytest.raises(TextValidationError) as exc1:
        InputValidator.validate_and_sanitize_text("hi")
    assert "at least 3 characters" in str(exc1.value)

    with pytest.raises(TextValidationError) as exc2:
        InputValidator.validate_and_sanitize_text("a")
    assert "at least 3 characters" in str(exc2.value)

    # Empty and whitespace-only are rejected
    with pytest.raises(TextValidationError) as exc3:
        InputValidator.validate_and_sanitize_text("")
    assert "empty or whitespace-only" in str(exc3.value)

    with pytest.raises(TextValidationError) as exc4:
        InputValidator.validate_and_sanitize_text("   \n\t   ")
    assert "empty or whitespace-only" in str(exc4.value)


def test_text_validation_multilingual_preservation() -> None:
    """Unicode normalization via NFKC preserves Indic and Arabic characters
    without damage or corruption.
    """
    malayalam = "റോഡിൽ വലിയ കുഴി ഉണ്ട്"
    res_ml = InputValidator.validate_and_sanitize_text(malayalam)
    assert res_ml.cleaned_text == malayalam

    hindi = "सड़क पर बड़ा गड्ढा है"
    res_hi = InputValidator.validate_and_sanitize_text(hindi)
    assert res_hi.cleaned_text == hindi

    arabic = "هناك حفرة كبيرة في الطريق"
    res_ar = InputValidator.validate_and_sanitize_text(arabic)
    assert res_ar.cleaned_text == arabic


def test_text_validation_repeated_characters_behavior() -> None:
    """Clarify repeated-character policy: legitimate numbers/punctuation are kept/compressed,
    while spam runs are rejected.
    """
    # Legitimate numbers like "100000" (5 zeros < 20 run limit) are preserved cleanly
    res_num = InputValidator.validate_and_sanitize_text("Road budget estimated 100000 INR")
    assert "100000" in res_num.cleaned_text
    assert len(res_num.warnings) == 0

    # Punctuation under 20 chars is preserved
    res_punc = InputValidator.validate_and_sanitize_text("What is happening here?????")
    assert "?????" in res_punc.cleaned_text

    # Excessive repeated punctuation (>= 20 identical chars) is compressed to 3 chars with warning
    res_dots = InputValidator.validate_and_sanitize_text("Pothole danger" + "." * 25)
    assert "..." in res_dots.cleaned_text
    assert "." * 4 not in res_dots.cleaned_text
    assert "EXCESSIVE_PUNCTUATION_COMPRESSED" in res_dots.warnings

    # Excessive non-punctuation character runs (>= 20 identical letters) are rejected as spam
    with pytest.raises(TextValidationError) as exc:
        InputValidator.validate_and_sanitize_text("Hazard" + "x" * 22)
    assert "excessive repeated character run" in str(exc.value)


# ===========================================================================
# 2. FILENAME DATA-LEAKAGE REVIEW REGRESSION
# ===========================================================================


def test_filename_invariance_regression(client: TestClient) -> None:
    """Identical image bytes and text produce 100% identical AI predictions regardless of filename.

    Proves that filenames like 'pothole.jpg', 'garbage.jpg', 'water_leak.jpg', or 'IMG_0001.jpg'
    do NOT leak into or bias category, confidence, severity, priority, or review routing.
    """
    img_b64 = _make_test_image_b64("JPEG", (120, 120))
    shared_description = "Continuous water leakage flooding pedestrian footpath"

    test_filenames = [
        "pothole.jpg",
        "garbage.jpg",
        "water_leak.jpg",
        "streetlight.jpg",
        "IMG_20260912_104230.jpg",
        "camera_capture_raw.jpg",
    ]

    predictions: list[dict[str, Any]] = []

    for filename in test_filenames:
        create_res = client.post(
            "/api/v1/reports",
            json={
                "location": {"latitude": 12.9716, "longitude": 77.5946},
                "description": shared_description,
                "evidence": [
                    {
                        "evidence_type": "IMAGE",
                        "storage_uri": filename,
                        "data_base64": img_b64,
                        "mime_type": "image/jpeg",
                    }
                ],
            },
        )
        assert create_res.status_code == 201
        report_id = create_res.json()["id"]

        ai_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
        assert ai_res.status_code == 202

        get_res = client.get(f"/api/v1/reports/{report_id}/ai")
        assert get_res.status_code == 200
        analysis = get_res.json()["ai_analysis"]
        norm = analysis["normalized_prediction"]

        predictions.append(
            {
                "predicted_category": norm["predicted_category"],
                "confidence": norm["confidence"],
                "severity": norm["severity"],
                "priority": norm["priority"],
                "evidence_agreement": norm["evidence_agreement"],
                "requires_review": norm["requires_review"],
            }
        )

    # All predictions must be bit-for-bit identical regardless of filename
    baseline = predictions[0]
    for idx, p in enumerate(predictions[1:], start=1):
        assert p["predicted_category"] == baseline["predicted_category"], (
            f"Filename {test_filenames[idx]} produced different category: "
            f"{p['predicted_category']} vs {baseline['predicted_category']}"
        )
        assert p["confidence"] == baseline["confidence"], (
            f"Filename {test_filenames[idx]} produced different confidence: "
            f"{p['confidence']} vs {baseline['confidence']}"
        )
        assert p["severity"] == baseline["severity"]
        assert p["priority"] == baseline["priority"]
        assert p["evidence_agreement"] == baseline["evidence_agreement"]
        assert p["requires_review"] == baseline["requires_review"]


# ===========================================================================
# 3. UNIMODAL FALLBACK & MODALITY AGREEMENT INVARIANTS
# ===========================================================================


def test_unimodal_fallback_does_not_claim_modality_agreement(client: TestClient) -> None:
    """When a report has no image or a corrupt image, modality agreement is NOT claimed
    (returns None).
    """
    # 1. Missing image report
    create_res = client.post(
        "/api/v1/reports",
        json={
            "location": {"latitude": 12.9716, "longitude": 77.5946},
            "description": "Blown street lamp causing complete darkness on corner",
            "evidence": [],
        },
    )
    assert create_res.status_code == 201
    rep_id = create_res.json()["id"]

    proc_res = client.post(f"/api/v1/reports/{rep_id}/ai/process")
    assert proc_res.status_code == 202

    ai_res = client.get(f"/api/v1/reports/{rep_id}/ai")
    ai_data = ai_res.json()
    analysis = ai_data["ai_analysis"]

    # evidence_agreement must be None, NOT fabricated or claimed as 0.50
    assert analysis["evidence_agreement"] is None
    assert analysis["normalized_prediction"]["evidence_agreement"] is None

    # review_required is mandatory on unimodal fallback
    assert analysis["review_required"] is True
    assert "IMAGE_UNAVAILABLE_FALLBACK" in analysis["normalized_prediction"]["warnings"]

    # In telemetry, bypassed vision stage duration is None (not falsely 0 ms)
    timing = analysis["normalized_prediction"]["timing_breakdown"]
    assert timing["vision_inference_ms"] is None


def test_timing_telemetry_invariants(client: TestClient) -> None:
    """Timing breakdown values are non-negative, report measured durations, and
    declare hardware acceleration as NONE.
    """
    create_res = client.post(
        "/api/v1/reports",
        json={
            "location": {"latitude": 12.9716, "longitude": 77.5946},
            "description": "Large road defect crater on cross street",
            "evidence": [],
        },
    )
    rep_id = create_res.json()["id"]
    client.post(f"/api/v1/reports/{rep_id}/ai/process")

    ai_res = client.get(f"/api/v1/reports/{rep_id}/ai")
    norm = ai_res.json()["ai_analysis"]["normalized_prediction"]

    timing = norm["timing_breakdown"]
    assert timing["intake_validation_ms"] is not None and timing["intake_validation_ms"] >= 0
    assert timing["text_inference_ms"] is not None and timing["text_inference_ms"] >= 0
    assert timing["fusion_ms"] is not None and timing["fusion_ms"] >= 0
    assert timing["decision_ms"] is not None and timing["decision_ms"] >= 0
    assert timing["normalization_ms"] is not None and timing["normalization_ms"] >= 0
    assert timing["total_pipeline_ms"] is not None and timing["total_pipeline_ms"] >= 0

    assert norm["hardware_acceleration"] == "NONE"
