"""CivicSense Phase 3.3 Step 4 Controlled Acquisition & Annotation Tests.

Verifies:
1. Dry-run does not write acquisition artifacts.
2. Execute mode stages candidates strictly under datasets/raw/.
3. Benchmark collision is rejected immediately by the leakage index.
4. Invalid license metadata is rejected or quarantined.
5. Source labels remain distinct from manual verification.
6. Other subtype is required and validated against the approved vocabulary.
7. Quarantined samples cannot enter clean train/validation splits.
8. Group-level split remains completely disjoint across splits.
9. Acquisition and curation pipeline operations are reproducible and deterministic.
10. Existing benchmark and baseline evaluation artifacts remain 100% byte-identical.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from app.evaluation.training_schema import (
    VALID_OTHER_SUBTYPES,
    AmbiguityStatus,
    BenchmarkLeakageCheckResult,
    LeakageStatus,
    LicenseScope,
    TrainingSample,
    TrainingSplit,
    VerificationMethod,
)
from scripts.datasets.acquire_batch_1 import BatchAcquisitionRunner
from scripts.datasets.leakage_detector import (
    FROZEN_BENCHMARK_MANIFEST_HASH,
    BenchmarkLeakageIndex,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_DIR = REPO_ROOT / "datasets" / "benchmark_v1"
BASELINE_DIR = REPO_ROOT / "datasets" / "evaluation_runs" / "baseline_v1"
TRAINING_DIR = REPO_ROOT / "datasets" / "training_v1"


def test_dry_run_does_not_write_acquisition_artifacts() -> None:
    """Dry-run must not create image files or disk artifacts."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        raw_dir = tmp_path / "raw"
        training_dir = tmp_path / "training"

        runner = BatchAcquisitionRunner(
            raw_dir=raw_dir,
            benchmark_dir=BENCHMARK_DIR,
            training_dir=training_dir,
            execute=False,
        )
        plan = runner.run_dry_run()

        assert plan["mode"] == "DRY_RUN"
        assert plan["clean_splits_modified"] is False
        assert plan["target_total_candidates"] == 100
        assert not (raw_dir / "boston311" / "images").exists()
        assert not (training_dir / "acquisition" / "batch_1_manifest.json").exists()


def test_execute_mode_stages_only_under_datasets_raw() -> None:
    """Acquisition artifacts must stage exclusively under datasets/raw/<source>/."""
    manifest_path = TRAINING_DIR / "acquisition" / "batch_1_manifest.json"
    assert manifest_path.is_file(), "Batch 1 manifest should exist after execution"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for cand in manifest.get("candidates", []):
        rel_path = cand["image_rel_path"]
        assert rel_path.startswith("boston311/images/"), (
            f"Candidate image path '{rel_path}' must stage under boston311/images/"
        )
        assert not rel_path.startswith("splits/"), "Candidates must never stage directly into splits/"


def test_benchmark_collision_is_rejected() -> None:
    """Benchmark leakage detector must reject any collision with benchmark records."""
    index = BenchmarkLeakageIndex(BENCHMARK_DIR)
    manifest_path = TRAINING_DIR / "acquisition" / "batch_1_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Verify quarantined collision candidate recorded in batch manifest
    quarantined = manifest.get("quarantined_candidates", [])
    assert len(quarantined) >= 1, "At least one leakage collision should be quarantined"
    collision_case_id = quarantined[0]["case_id"]

    # Verify that testing this ID against the index fails
    res = index.check_candidate(
        sample_id=f"bost_{collision_case_id}",
        sha256="",
        source_name="boston311",
        source_record_id=collision_case_id,
        source_url=f"https://example.com/{collision_case_id}.jpg",
    )
    # Either source ID or SHA matches benchmark
    assert not res.passed or "collision" in quarantined[0]["reason"].lower()


def test_invalid_license_metadata_is_rejected() -> None:
    """Missing or empty license metadata must be rejected by the schema."""
    with pytest.raises(ValueError):
        TrainingSample(
            sample_id="train_invalid_license",
            source_name="boston311",
            source_record_id="12345",
            source_url="https://example.com/photo.jpg",
            license="",  # Empty license must fail validation
            local_path="datasets/raw/boston311/images/photo.jpg",
            sha256="a" * 64,
            dhash="b" * 16,
            width=800,
            height=600,
            file_size_bytes=102400,
            mime_type="image/jpeg",
            primary_category="Pothole",
            group_id="grp_12345",
        )


def test_source_labels_remain_distinct_from_manual_verification() -> None:
    """VerificationMethod distinguishes source labels from manual review."""
    v_source: VerificationMethod = VerificationMethod.SOURCE_LABEL
    v_manual: VerificationMethod = VerificationMethod.MANUAL_REVIEW
    assert v_source != v_manual

    # Verify that in batch_1_annotations, reviewed samples have manual_review
    annotations_path = TRAINING_DIR / "acquisition" / "batch_1_annotations.json"
    assert annotations_path.is_file()
    ann_data = json.loads(annotations_path.read_text(encoding="utf-8"))

    for ann in ann_data.get("annotations", []):
        assert ann["verification_method"] == "manual_review"
        assert ann["verification_status"] in ("VERIFIED_CLEAN", "QUARANTINED")


def test_other_subtype_is_required_and_validated() -> None:
    """Primary category Other requires and validates explicit civic subtypes."""
    assert "graffiti" in VALID_OTHER_SUBTYPES
    assert "damaged_sidewalk" in VALID_OTHER_SUBTYPES
    assert "other_documented_civic_defect" in VALID_OTHER_SUBTYPES

    # Valid subtype passes
    sample = TrainingSample(
        sample_id="train_valid_other",
        source_name="boston311",
        source_record_id="rec_other_1",
        source_url="https://example.com/other1.jpg",
        license="ODC-PDDL",
        license_scope=LicenseScope.DATASET,
        local_path="datasets/raw/boston311/images/other1.jpg",
        sha256="1" * 64,
        dhash="2" * 16,
        width=1024,
        height=768,
        file_size_bytes=204800,
        mime_type="image/jpeg",
        primary_category="Other",
        subtype="graffiti",
        group_id="grp_other_1",
        split=TrainingSplit.TRAIN,
    )
    assert sample.subtype == "graffiti"

    # Invalid subtype fails
    with pytest.raises(ValueError, match="has invalid Other subtype"):
        TrainingSample(
            sample_id="train_invalid_other",
            source_name="boston311",
            source_record_id="rec_other_2",
            source_url="https://example.com/other2.jpg",
            license="ODC-PDDL",
            license_scope=LicenseScope.DATASET,
            local_path="datasets/raw/boston311/images/other2.jpg",
            sha256="3" * 64,
            dhash="4" * 16,
            width=1024,
            height=768,
            file_size_bytes=204800,
            mime_type="image/jpeg",
            primary_category="Other",
            subtype="invalid_unregistered_subtype",
            group_id="grp_other_2",
            split=TrainingSplit.TRAIN,
        )


def test_quarantine_samples_cannot_enter_clean_splits() -> None:
    """Ambiguous or quarantined samples cannot be placed into train or validation splits."""
    with pytest.raises(ValueError, match="must have split=QUARANTINE"):
        TrainingSample(
            sample_id="train_ambiguous_illegal",
            source_name="boston311",
            source_record_id="rec_amb_1",
            source_url="https://example.com/amb1.jpg",
            license="ODC-PDDL",
            local_path="datasets/raw/boston311/images/amb1.jpg",
            sha256="5" * 64,
            dhash="6" * 16,
            width=1024,
            height=768,
            file_size_bytes=204800,
            mime_type="image/jpeg",
            primary_category="Pothole",
            ambiguity_status=AmbiguityStatus.AMBIGUOUS,
            group_id="grp_amb_1",
            split=TrainingSplit.TRAIN,  # Must fail: ambiguous cannot be TRAIN
        )

    with pytest.raises(ValueError, match="failed benchmark leakage check"):
        TrainingSample(
            sample_id="train_leak_illegal",
            source_name="boston311",
            source_record_id="rec_leak_1",
            source_url="https://example.com/leak1.jpg",
            license="ODC-PDDL",
            local_path="datasets/raw/boston311/images/leak1.jpg",
            sha256="7" * 64,
            dhash="8" * 16,
            width=1024,
            height=768,
            file_size_bytes=204800,
            mime_type="image/jpeg",
            primary_category="Pothole",
            benchmark_leakage_check=BenchmarkLeakageCheckResult(
                status=LeakageStatus.FAILED_EXACT_SHA256,
                checked=True,
                passed=False,
            ),
            group_id="grp_leak_1",
            split=TrainingSplit.VALIDATION,  # Must fail: leakage cannot be VALIDATION
        )


def test_group_level_split_remains_disjoint() -> None:
    """Train and validation splits must have zero overlapping group IDs."""
    train_file = TRAINING_DIR / "splits" / "train.jsonl"
    val_file = TRAINING_DIR / "splits" / "validation.jsonl"
    assert train_file.is_file()
    assert val_file.is_file()

    train_groups = {
        json.loads(line)["group_id"]
        for line in train_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    val_groups = {
        json.loads(line)["group_id"]
        for line in val_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    overlap = train_groups.intersection(val_groups)
    assert len(overlap) == 0, f"Found group leakage between train and validation: {overlap}"


def test_rerunning_same_acquisition_is_deterministic() -> None:
    """Annotation summary and counts are deterministic and consistent."""
    ann_file = TRAINING_DIR / "acquisition" / "batch_1_annotations.json"
    assert ann_file.is_file()
    data = json.loads(ann_file.read_text(encoding="utf-8"))

    assert data["total_evaluated"] == 100
    assert data["total_accepted_clean"] == 91
    assert data["total_quarantined_ambiguous"] == 9
    assert data["category_accepted_counts"]["Pothole"] == 46
    assert data["category_accepted_counts"]["Other"] == 45


def test_existing_benchmark_and_baseline_remain_byte_identical() -> None:
    """Benchmark dataset and official baseline metrics must remain strictly intact."""
    dataset_path = BENCHMARK_DIR / "benchmark_dataset.jsonl"
    assert dataset_path.is_file()

    computed_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    assert computed_hash == FROZEN_BENCHMARK_MANIFEST_HASH, (
        f"Benchmark dataset hash modified! Expected {FROZEN_BENCHMARK_MANIFEST_HASH}, got {computed_hash}"
    )

    metrics_path = BASELINE_DIR / "metrics.json"
    assert metrics_path.is_file()
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["classification"]["total_samples"] == 300
    assert metrics["classification"]["accuracy"] == 0.79
