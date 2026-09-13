"""CivicSense Phase 3.2 Step 6.5 — Baseline Forensics Unit Tests.

Validates the integrity, determinism, and mathematical invariants of:
1. Benchmark immutability (hash, count, category balance).
2. Official baseline preservation (unmodified baseline runs).
3. Text ablation determinism and zero sample loss (300 samples across all 7 ablations).
4. Keyword masking reproducibility (lexical coverage and regex masking).
5. Vision diagnostic schema integrity and 100% image decoding.
6. Fusion diagnostics sample ID preservation and confidence formula invariants.
7. Confusion matrix sum conservation (strictly equals 300 per condition).
8. Resilient handling of missing, empty, or corrupted image and text inputs.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from app.evaluation.evaluator import OfflineDeterministicEvaluator, _OfflineEvidenceAdapter
from app.evaluation.runner import CANONICAL_BENCHMARK_CATEGORIES
from app.evaluation.schema import EvaluationSample
from app.services.ai.vision_analyzer import PrototypeVisionAnalyzer
from scripts.evaluate_baseline_forensics import (
    KEYWORD_MASKING_TERMS,
    mask_text_keywords,
    run_text_ablation_audit,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_DIR = REPO_ROOT / "datasets" / "benchmark_v1"
FORENSICS_DIR = REPO_ROOT / "datasets" / "evaluation_runs" / "baseline_forensics_v1"
OFFICIAL_BASELINE_DIR = REPO_ROOT / "datasets" / "evaluation_runs" / "baseline_v1"
OFFICIAL_VISION_DIR = REPO_ROOT / "datasets" / "evaluation_runs" / "baseline_vision_only"
OFFICIAL_TEXT_DIR = REPO_ROOT / "datasets" / "evaluation_runs" / "baseline_text_only"


# ===========================================================================
# 1. BENCHMARK IMMUTABILITY TESTS
# ===========================================================================


def test_benchmark_immutability_and_hash_integrity() -> None:
    """Benchmark dataset file hash strictly matches the frozen manifest."""
    manifest_path = BENCHMARK_DIR / "manifest.json"
    dataset_path = BENCHMARK_DIR / "benchmark_dataset.jsonl"

    assert manifest_path.is_file(), f"Manifest missing at {manifest_path}"
    assert dataset_path.is_file(), f"Benchmark dataset missing at {dataset_path}"

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    # Compute actual sha256 of the frozen benchmark_dataset.jsonl
    hasher = hashlib.sha256()
    with open(dataset_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()

    assert manifest.get("integrity_hash") == actual_hash
    assert manifest.get("total_sample_count") == 300


def test_benchmark_category_balance() -> None:
    """Benchmark contains exactly 300 samples with 50 per canonical category."""
    dataset_path = BENCHMARK_DIR / "benchmark_dataset.jsonl"
    category_counts: dict[str, int] = {cat: 0 for cat in CANONICAL_BENCHMARK_CATEGORIES}

    with open(dataset_path, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 300

    for line in lines:
        data = json.loads(line)
        cat = data.get("canonical_category")
        assert cat in category_counts
        category_counts[cat] += 1

    for cat in CANONICAL_BENCHMARK_CATEGORIES:
        assert category_counts[cat] == 50, f"Category {cat} has count {category_counts[cat]} != 50"


# ===========================================================================
# 2. OFFICIAL BASELINE ARTIFACT PRESERVATION TESTS
# ===========================================================================


def test_official_baseline_runs_unmodified() -> None:
    """Official baseline runs remain intact and unmutated by forensics."""
    # 1. Official multimodal baseline
    multi_metrics = OFFICIAL_BASELINE_DIR / "metrics.json"
    assert multi_metrics.is_file()
    with open(multi_metrics, encoding="utf-8") as f:
        m_data = json.load(f)
    assert m_data["classification"]["total_samples"] == 300
    assert m_data["classification"]["accuracy"] == 0.79
    assert m_data["confidence"]["manual_review_count"] == 299

    # 2. Official vision-only baseline
    vision_metrics = OFFICIAL_VISION_DIR / "metrics.json"
    assert vision_metrics.is_file()
    with open(vision_metrics, encoding="utf-8") as f:
        v_data = json.load(f)
    assert v_data["classification"]["total_samples"] == 300
    assert v_data["classification"]["accuracy"] == 0.1667

    # 3. Official text-only baseline
    text_metrics = OFFICIAL_TEXT_DIR / "metrics.json"
    assert text_metrics.is_file()
    with open(text_metrics, encoding="utf-8") as f:
        t_data = json.load(f)
    assert t_data["classification"]["total_samples"] == 300
    assert t_data["classification"]["accuracy"] == 0.79


# ===========================================================================
# 3. TEXT ABLATION DETERMINISM & ZERO SAMPLE LOSS TESTS
# ===========================================================================


def test_text_ablation_results_completeness() -> None:
    """Forensic text ablation results cover all 7 conditions with zero sample loss."""
    results_path = FORENSICS_DIR / "text_ablation_results.json"
    assert results_path.is_file()

    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("manifest_integrity_hash") is not None
    ablations = data.get("ablations", {})

    expected_keys = [
        "A_original",
        "B_lowercased",
        "C_whitespace_normalized",
        "D_empty",
        "E_generic_neutral",
        "F_keyword_masked",
        "G_truncated_30",
    ]

    assert set(ablations.keys()) == set(expected_keys)

    for key in expected_keys:
        res = ablations[key]
        assert res["total_samples"] == 300
        assert res["correct_count"] + res["error_count"] == 300
        assert 0.0 <= res["accuracy"] <= 1.0
        assert 0.0 <= res["macro_f1"] <= 1.0


def test_text_ablation_synthetic_fixture_execution() -> None:
    """run_text_ablation_audit correctly transforms and evaluates arbitrary samples."""
    samples = [
        EvaluationSample(
            sample_id="test_pothole_01",
            image_rel_path="Pothole/test1.jpg",
            source_dataset="test",
            source_record_id="rec_01",
            canonical_category="Pothole",
            original_category="pothole",
            category_confidence=1.0,
            license="CC0-1.0",
            license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            attribution="Test contributor",
            sha256="a" * 64,
            phash="0" * 16,
            text_description="Deep pothole in asphalt road",
        ),
        EvaluationSample(
            sample_id="test_other_01",
            image_rel_path="Other/test2.jpg",
            source_dataset="test",
            source_record_id="rec_02",
            canonical_category="Other",
            original_category="bench",
            category_confidence=1.0,
            license="CC0-1.0",
            license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            attribution="Test contributor",
            sha256="b" * 64,
            phash="1" * 16,
            text_description="Broken wooden bench in city park",
        ),
    ]

    evaluator = OfflineDeterministicEvaluator()
    results, cms = run_text_ablation_audit(samples, evaluator, official_text_accuracy=0.79)

    assert len(results) == 7
    assert len(cms) == 7

    # Original text should recognize pothole
    assert results["A_original"]["total_samples"] == 2
    # In empty condition, both default to Other (accuracy 0.50 since 1 true Other)
    assert results["D_empty"]["accuracy"] == 0.50
    # In keyword-masked condition, "pothole" and "asphalt" are masked
    assert results["F_keyword_masked"]["total_samples"] == 2


# ===========================================================================
# 4. KEYWORD MASKING REPRODUCIBILITY TESTS
# ===========================================================================


def test_keyword_masking_rules_and_terms() -> None:
    """Keyword masking rules cover all major civic defect categories."""
    assert "Pothole" in KEYWORD_MASKING_TERMS
    assert "Garbage" in KEYWORD_MASKING_TERMS
    assert "Water Leakage" in KEYWORD_MASKING_TERMS
    assert "Streetlight" in KEYWORD_MASKING_TERMS
    assert "Road Damage" in KEYWORD_MASKING_TERMS
    assert "Drainage" in KEYWORD_MASKING_TERMS

    total_patterns = sum(len(terms) for terms in KEYWORD_MASKING_TERMS.values())
    assert total_patterns >= 35


@pytest.mark.parametrize(
    ("input_text", "expected_masked"),
    [
        (
            "Large pothole in the asphalt roadway",
            "Large [MASKED] in the [MASKED] roadway",
        ),
        (
            "Garbage overflowing from trash bin with debris",
            "[MASKED] overflowing from [MASKED] [MASKED] with [MASKED]",
        ),
        (
            "Streetlight pole broken and lamp bulb is out",
            "[MASKED] [MASKED] [MASKED] and [MASKED] [MASKED] is out",
        ),
        (
            "Water leak from ruptured pipe causing flood",
            "[MASKED] [MASKED] from ruptured [MASKED] causing [MASKED]",
        ),
        (
            "Pavement crack along the road",
            "[MASKED] [MASKED] along the [MASKED]",
        ),
        (
            "Clean civic park with trees",
            "Clean civic park with trees",
        ),
    ],
)
def test_mask_text_keywords_reproducibility(input_text: str, expected_masked: str) -> None:
    """Civic defect keywords are deterministically masked with [MASKED]."""
    masked = mask_text_keywords(input_text)
    assert masked == expected_masked


# ===========================================================================
# 5. VISION DIAGNOSTIC INTEGRITY TESTS
# ===========================================================================


def test_vision_diagnostics_integrity() -> None:
    """Vision diagnostics report verifies 100% image decoding without failures."""
    diag_path = FORENSICS_DIR / "vision_diagnostics.json"
    pred_path = FORENSICS_DIR / "vision_predictions_diagnostics.jsonl"

    assert diag_path.is_file()
    assert pred_path.is_file()

    with open(diag_path, encoding="utf-8") as f:
        diag = json.load(f)

    summary = diag.get("summary", {})
    assert summary.get("total_samples") == 300
    assert summary.get("image_load_success_count") == 300
    assert summary.get("image_processing_failures_count") == 0
    assert summary.get("prediction_distribution") == {"Other": 300}
    assert summary.get("vision_only_accuracy") == 0.1667

    # Verify per-sample JSONL diagnostics
    with open(pred_path, encoding="utf-8") as f:
        lines = [json.loads(line.strip()) for line in f if line.strip()]

    assert len(lines) == 300
    for entry in lines:
        assert entry["image_load_success"] is True
        assert len(entry["image_dimensions"]) == 2
        assert entry["image_dimensions"][0] > 0
        assert entry["image_dimensions"][1] > 0
        assert entry["vision_output_category"] == "Other"
        assert entry["vision_confidence"] == 0.50
        assert "Prototype Vision Analyzer" in entry["model_name"]


# ===========================================================================
# 6. FUSION & CONFIDENCE FORENSICS TESTS
# ===========================================================================


def test_fusion_diagnostics_sample_preservation_and_formula() -> None:
    """Fusion diagnostics accurately track 300 benchmark samples and math invariants."""
    fusion_diag_path = FORENSICS_DIR / "fusion_diagnostics.json"
    fusion_samples_path = FORENSICS_DIR / "fusion_sample_diagnostics.jsonl"
    dataset_path = BENCHMARK_DIR / "benchmark_dataset.jsonl"

    with open(fusion_diag_path, encoding="utf-8") as f:
        f_diag = json.load(f)

    summary = f_diag.get("summary", {})
    assert summary.get("total_samples") == 300
    thresh_metrics = summary.get("threshold_metrics", {})
    assert thresh_metrics.get("below_threshold_percentage") == 99.67
    assert thresh_metrics.get("above_threshold_count") == 1
    assert thresh_metrics.get("below_threshold_count") == 299

    # Verify sample ID set match
    with open(dataset_path, encoding="utf-8") as f:
        benchmark_sample_ids = {json.loads(line)["sample_id"] for line in f if line.strip()}

    with open(fusion_samples_path, encoding="utf-8") as f:
        sample_entries = [json.loads(line) for line in f if line.strip()]

    assert len(sample_entries) == 300
    fusion_sample_ids = {entry["sample_id"] for entry in sample_entries}
    assert fusion_sample_ids == benchmark_sample_ids

    # Verify fusion formula: round(t_conf * 0.45 + v_conf * 0.35 + agreement * 0.20, 2)
    auto_accepted_found = 0
    for entry in sample_entries:
        t_conf = entry["text_confidence"]
        v_conf = entry["vision_confidence"]
        agr = entry["fusion_evidence_agreement"]
        expected_fused = round((t_conf * 0.45) + (v_conf * 0.35) + (agr * 0.20), 2)
        assert abs(entry["final_confidence"] - expected_fused) < 0.02

        if not entry["review_required"]:
            auto_accepted_found += 1
            assert entry["sample_id"] == "pilot_wmlight_13644347"
            assert entry["final_confidence"] >= 0.70

    assert auto_accepted_found == 1


# ===========================================================================
# 7. CONFUSION MATRIX CONSERVATION TESTS
# ===========================================================================


def test_confusion_matrix_sum_conservation() -> None:
    """Every text ablation confusion matrix sums strictly to 300."""
    cm_path = FORENSICS_DIR / "text_ablation_confusion_matrices.json"
    assert cm_path.is_file()

    with open(cm_path, encoding="utf-8") as f:
        cms: dict[str, Any] = json.load(f)

    for key, cm_data in cms.items():
        assert cm_data["total_samples"] == 300
        assert cm_data["matrix_sum"] == 300

        matrix = cm_data["matrix"]
        total_sum = sum(sum(row) for row in matrix)
        assert total_sum == 300, f"Condition {key} matrix sum was {total_sum} != 300"

        # Each row corresponds to a ground-truth class with support 50
        for i, row in enumerate(matrix):
            row_sum = sum(row)
            assert row_sum == 50, f"Condition {key} row {i} ({cm_data['classes'][i]}) sum was {row_sum} != 50"


# ===========================================================================
# 8. RESILIENT HANDLING OF MISSING / MALFORMED INPUTS TESTS
# ===========================================================================


def test_evaluator_missing_and_empty_inputs_graceful_handling() -> None:
    """OfflineDeterministicEvaluator handles missing or corrupted inputs without fatal crash."""
    evaluator = OfflineDeterministicEvaluator()

    # 1. None for both image and text -> unimodal fallback policy penalty (0.50 * 0.70 = 0.35)
    res_none = evaluator.evaluate(image_bytes=None, text=None)
    assert res_none.predicted_category == "Other"
    assert res_none.confidence == 0.35
    assert res_none.requires_review is True

    # 2. Empty string text and None image -> unimodal fallback penalty
    res_empty_text = evaluator.evaluate(image_bytes=None, text="")
    assert res_empty_text.predicted_category == "Other"
    assert res_empty_text.confidence == 0.35
    assert res_empty_text.requires_review is True

    # 3. Empty bytes image with valid text
    res_empty_img = evaluator.evaluate(image_bytes=b"", text="Pothole in roadway")
    assert res_empty_img.predicted_category == "Pothole"
    assert res_empty_img.confidence > 0.0
    assert res_empty_img.requires_review is True

    # 4. Corrupted image bytes with valid text
    res_corrupt_img = evaluator.evaluate(image_bytes=b"invalid-image-header", text="Trash everywhere")
    assert res_corrupt_img.predicted_category == "Garbage"


def test_prototype_vision_analyzer_handles_all_inputs() -> None:
    """PrototypeVisionAnalyzer returns consistent fallback for any evidence input."""
    analyzer = PrototypeVisionAnalyzer()

    # Empty evidences list -> missing image fallback
    res_empty = analyzer.analyze([])
    assert res_empty["has_image"] is False
    assert res_empty["predicted_category"] is None
    assert res_empty["confidence"] == 0.30

    # Single image evidence with neutral metadata
    adapter = _OfflineEvidenceAdapter()
    res_image = analyzer.analyze([adapter])  # type: ignore[list-item]
    assert res_image["has_image"] is True
    assert res_image["predicted_category"] == "Other"
    assert res_image["confidence"] == 0.50
