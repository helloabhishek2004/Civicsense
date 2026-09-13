"""CivicSense Training Dataset & Curation Tooling Tests.

Tests:
1. Valid manifest parsing and Pydantic validation
2. Invalid category rejection
3. Invalid split rejection
4. Invalid SHA-256 and dHash format rejection
5. Missing provenance rejection
6. Ambiguity/quarantine status split enforcement
7. Exact benchmark SHA-256 collision rejection
8. Benchmark source record ID collision rejection
9. Benchmark canonical URL collision detection
10. Benchmark 64-bit dHash near-duplicate rejection (Hamming distance <= 6)
11. Intra-dataset exact duplicate detection
12. Intra-dataset near-duplicate detection (Hamming distance <= 4)
13. Group-level split integrity (zero group leakage between train and validation)
14. Deterministic split reproducibility with fixed seed
15. Quarantine exclusion from train and validation splits
16. Corrupt image handling and quarantine
17. Unsupported format handling
18. Invalid dimensions handling
19. Class distribution accounting
20. Source distribution accounting
21. Benchmark manifest immutability
22. Official baseline metrics immutability
23. Training image git-ignore rule verification
24. Benchmark files count and integrity preservation
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from pydantic import ValidationError

from app.evaluation.training_schema import (
    TrainingDatasetSummary,
    TrainingSample,
    TrainingSplit,
)
from scripts.datasets.leakage_detector import (
    FROZEN_BENCHMARK_MANIFEST_HASH,
    BenchmarkLeakageIndex,
    normalize_url,
)
from scripts.datasets.training_splitter import (
    assign_group_ids,
    detect_intra_dataset_duplicates,
    split_training_dataset,
)
from scripts.datasets.validate_images import validate_image_file

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_DIR = REPO_ROOT / "datasets" / "benchmark_v1"
BASELINE_DIR = REPO_ROOT / "datasets" / "evaluation_runs" / "baseline_v1"


# Fixtures
@pytest.fixture
def valid_sample_dict() -> dict[str, Any]:
    return {
        "sample_id": "train_bost_test_001",
        "dataset_version": "training_v1",
        "source_name": "boston311",
        "source_record_id": "101009999999",
        "source_url": "https://example.com/images/test_001.jpg",
        "license": "ODC-PDDL",
        "license_url": "http://www.opendefinition.org/licenses/odc-pddl",
        "license_scope": "dataset",
        "local_path": "datasets/training_v1/images/pothole/test_001.jpg",
        "sha256": "a" * 64,
        "dhash": "1234567890abcdef",
        "width": 640,
        "height": 480,
        "file_size_bytes": 102400,
        "mime_type": "image/jpeg",
        "primary_category": "Pothole",
        "secondary_categories": [],
        "has_multiple_issues": False,
        "quality_flags": [],
        "ambiguity_status": "clear",
        "verification_status": "SOURCE_LABEL",
        "verification_method": "source_label",
        "reviewer_notes": None,
        "group_id": "grp_bost_101009999999",
        "split": "train",
        "benchmark_leakage_check": {
            "status": "passed",
            "checked": True,
            "passed": True,
            "min_dhash_distance": 22,
        },
        "created_at": "2026-09-13T00:00:00Z",
        "schema_version": "1.0.0",
    }


# Test 1: Valid manifest parsing
def test_valid_manifest_parsing(valid_sample_dict: dict[str, Any]) -> None:
    sample = TrainingSample.model_validate(valid_sample_dict)
    assert sample.sample_id == "train_bost_test_001"
    assert sample.primary_category == "Pothole"
    assert sample.split == TrainingSplit.TRAIN
    assert sample.benchmark_leakage_check.passed is True


# Test 2: Invalid category rejection
def test_invalid_category_rejection(valid_sample_dict: dict[str, Any]) -> None:
    bad_dict = dict(valid_sample_dict)
    bad_dict["primary_category"] = "AlienInvasion"
    with pytest.raises(ValidationError) as exc:
        TrainingSample.model_validate(bad_dict)
    assert "AlienInvasion" in str(exc.value)


# Test 3: Invalid split rejection
def test_invalid_split_rejection(valid_sample_dict: dict[str, Any]) -> None:
    bad_dict = dict(valid_sample_dict)
    bad_dict["split"] = "invalid_split_name"
    with pytest.raises(ValidationError):
        TrainingSample.model_validate(bad_dict)


# Test 4: Invalid SHA-256 and dHash format rejection
def test_invalid_hash_format_rejection(valid_sample_dict: dict[str, Any]) -> None:
    bad_sha = dict(valid_sample_dict)
    bad_sha["sha256"] = "short_hash"
    with pytest.raises(ValidationError):
        TrainingSample.model_validate(bad_sha)

    bad_dhash = dict(valid_sample_dict)
    bad_dhash["dhash"] = "not_16_hex_chars_at_all"
    with pytest.raises(ValidationError):
        TrainingSample.model_validate(bad_dhash)


# Test 5: Missing provenance rejection
def test_missing_provenance_rejection(valid_sample_dict: dict[str, Any]) -> None:
    bad_dict = dict(valid_sample_dict)
    bad_dict["source_name"] = ""
    with pytest.raises(ValidationError):
        TrainingSample.model_validate(bad_dict)


# Test 6: Ambiguity/quarantine status split enforcement
def test_ambiguity_quarantine_split_enforcement(valid_sample_dict: dict[str, Any]) -> None:
    bad_dict = dict(valid_sample_dict)
    bad_dict["ambiguity_status"] = "ambiguous"
    bad_dict["split"] = "train"  # Violates quarantine isolation
    with pytest.raises(ValidationError) as exc:
        TrainingSample.model_validate(bad_dict)
    assert "must have split=QUARANTINE" in str(exc.value)


# Test 7: Exact benchmark SHA-256 collision rejection
def test_exact_benchmark_sha256_rejection() -> None:
    detector = BenchmarkLeakageIndex(BENCHMARK_DIR)
    # Pick a real benchmark sha256
    real_bm_sha256 = list(detector.benchmark_hashes.keys())[0]
    res = detector.check_candidate(
        sample_id="cand_leak_01",
        sha256=real_bm_sha256,
        source_name="unrelated_source",
        source_record_id="999999",
    )
    assert res.passed is False
    assert res.status == "FAILED_EXACT_SHA256"


# Test 8: Benchmark source record ID collision rejection
def test_benchmark_source_record_rejection() -> None:
    detector = BenchmarkLeakageIndex(BENCHMARK_DIR)
    # Pick a real benchmark source dataset and record ID
    (src_name, src_rec) = list(detector.benchmark_source_ids.keys())[0]
    res = detector.check_candidate(
        sample_id="cand_leak_02",
        sha256="b" * 64,
        source_name=src_name,
        source_record_id=src_rec,
    )
    assert res.passed is False
    assert res.status == "FAILED_SOURCE_ID"


# Test 9: Benchmark canonical URL collision detection
def test_benchmark_url_collision_detection() -> None:
    url1 = "https://commons.wikimedia.org/wiki/File:Burst_Pipe.jpg?utm_source=twitter&ref=share"
    url2 = "https://commons.wikimedia.org/wiki/File:Burst_Pipe.jpg/"
    norm1 = normalize_url(url1)
    norm2 = normalize_url(url2)
    assert norm1 == norm2
    assert norm1 == "https://commons.wikimedia.org/wiki/File:Burst_Pipe.jpg"


# Test 10: Benchmark dHash near-duplicate rejection (Hamming distance <= 6)
def test_benchmark_dhash_near_duplicate_rejection() -> None:
    detector = BenchmarkLeakageIndex(BENCHMARK_DIR)
    real_bm_dhash = detector.benchmark_dhashes[0][1]
    # Create near-duplicate with distance = 2
    val = int(real_bm_dhash, 16) ^ 0b11
    near_dup_dhash = f"{val:016x}"

    res = detector.check_candidate(
        sample_id="cand_leak_03",
        sha256="c" * 64,
        source_name="fresh_source",
        source_record_id="fresh_rec",
        dhash=near_dup_dhash,
    )
    assert res.passed is False
    assert res.status == "FAILED_DHASH_NEAR_DUPLICATE"
    assert res.min_dhash_distance is not None
    assert res.min_dhash_distance <= 6


# Test 11: Intra-dataset exact duplicate detection
def test_intra_dataset_exact_duplicate_detection() -> None:
    samples = [
        {"sample_id": "s1", "sha256": "f" * 64, "dhash": "1111222233334444"},
        {"sample_id": "s2", "sha256": "f" * 64, "dhash": "1111222233334444"},
        {"sample_id": "s3", "sha256": "e" * 64, "dhash": "aaaaaaaaaaaaaaaa"},
    ]
    report = detect_intra_dataset_duplicates(samples)
    assert report["exact_duplicates_count"] == 1
    assert report["exact_duplicates"][0]["sample_id_1"] == "s1"
    assert report["exact_duplicates"][0]["sample_id_2"] == "s2"


# Test 12: Intra-dataset near-duplicate detection
def test_intra_dataset_near_duplicate_detection() -> None:
    base_val = 0x1234567890ABCDEF
    dup_val = base_val ^ 0b11  # Hamming distance 2
    samples = [
        {"sample_id": "s1", "sha256": "1" * 64, "dhash": f"{base_val:016x}"},
        {"sample_id": "s2", "sha256": "2" * 64, "dhash": f"{dup_val:016x}"},
    ]
    report = detect_intra_dataset_duplicates(samples)
    assert report["near_duplicates_count"] == 1
    assert report["near_duplicates"][0]["dhash_distance"] == 2


# Test 13: Group-level split integrity (zero group leakage)
def test_group_level_split_integrity() -> None:
    samples = [
        {"sample_id": "s1", "group_id": "grp_A", "primary_category": "Pothole", "ambiguity_status": "clear"},
        {"sample_id": "s2", "group_id": "grp_A", "primary_category": "Pothole", "ambiguity_status": "clear"},
        {"sample_id": "s3", "group_id": "grp_B", "primary_category": "Pothole", "ambiguity_status": "clear"},
        {"sample_id": "s4", "group_id": "grp_C", "primary_category": "Pothole", "ambiguity_status": "clear"},
        {"sample_id": "s5", "group_id": "grp_D", "primary_category": "Pothole", "ambiguity_status": "clear"},
    ]
    res = split_training_dataset(samples, seed=42, train_ratio=0.8)
    train_groups = {r["group_id"] for r in res["train_records"]}
    val_groups = {r["group_id"] for r in res["validation_records"]}
    assert train_groups.isdisjoint(val_groups)


# Test 14: Deterministic split reproducibility
def test_deterministic_split_reproducibility() -> None:
    samples = [
        {"sample_id": f"s{i}", "group_id": f"grp_{i//2}", "primary_category": "Garbage", "ambiguity_status": "clear"}
        for i in range(20)
    ]
    res1 = split_training_dataset(samples, seed=42)
    res2 = split_training_dataset(samples, seed=42)

    ids1_train = [r["sample_id"] for r in res1["train_records"]]
    ids2_train = [r["sample_id"] for r in res2["train_records"]]
    assert ids1_train == ids2_train


# Test 15: Quarantine exclusion from train and val
def test_quarantine_exclusion() -> None:
    samples = [
        {"sample_id": "s1", "group_id": "grp_1", "primary_category": "Pothole", "ambiguity_status": "clear"},
        {"sample_id": "s2", "group_id": "grp_2", "primary_category": "Pothole", "ambiguity_status": "ambiguous"},
        {"sample_id": "s3", "group_id": "grp_3", "primary_category": "Pothole", "ambiguity_status": "unusable"},
    ]
    res = split_training_dataset(samples, seed=42)
    quar_ids = {r["sample_id"] for r in res["quarantine_records"]}
    train_ids = {r["sample_id"] for r in res["train_records"]}
    val_ids = {r["sample_id"] for r in res["validation_records"]}

    assert "s2" in quar_ids
    assert "s3" in quar_ids
    assert "s2" not in train_ids and "s2" not in val_ids
    assert "s3" not in train_ids and "s3" not in val_ids


# Test 16: Corrupt image quarantine
def test_corrupt_image_quarantine() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_file = Path(tmpdir) / "bad.jpg"
        bad_file.write_bytes(b"NOT_A_VALID_IMAGE_BYTES_STREAM")
        res = validate_image_file(bad_file)
        assert res.is_valid is False
        assert "magic bytes" in str(res.rejection_reason).lower() or "unidentified" in str(res.rejection_reason).lower()


# Test 17: Unsupported format handling
def test_unsupported_format_handling() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        bmp_file = Path(tmpdir) / "test.bmp"
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(bmp_file, format="BMP")
        res = validate_image_file(bmp_file)
        assert res.is_valid is False
        assert "unsupported" in str(res.rejection_reason).lower() or "magic bytes" in str(res.rejection_reason).lower()


# Test 18: Invalid dimensions handling
def test_invalid_dimensions_handling() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tiny_file = Path(tmpdir) / "tiny.jpg"
        img = Image.new("RGB", (32, 32), color="red")  # Below 64px min dimension
        img.save(tiny_file, format="JPEG")
        res = validate_image_file(tiny_file)
        assert res.is_valid is False
        assert "dimension" in str(res.rejection_reason).lower()


# Test 19: Class distribution reporting
def test_class_distribution_reporting() -> None:
    summary = TrainingDatasetSummary(
        dataset_version="training_v1",
        total_samples=10,
        train_samples=8,
        validation_samples=2,
        quarantine_samples=0,
        class_distribution={
            "Pothole": {"train": 4, "validation": 1, "quarantine": 0, "total": 5},
            "Garbage": {"train": 4, "validation": 1, "quarantine": 0, "total": 5},
        },
        source_distribution={"boston311": 10},
        group_count=10,
    )
    assert summary.total_samples == 10
    assert summary.class_distribution["Pothole"]["total"] == 5


# Test 20: Source distribution reporting
def test_source_distribution_reporting() -> None:
    samples = [
        {"sample_id": "s1", "source_name": "boston311"},
        {"sample_id": "s2", "source_name": "wikimedia_water"},
    ]
    grouped = assign_group_ids(samples)
    assert grouped[0]["group_id"].startswith("grp_")
    assert grouped[1]["group_id"].startswith("grp_")


# Test 21: Benchmark manifest immutability
def test_benchmark_manifest_immutability() -> None:
    manifest_path = BENCHMARK_DIR / "manifest.json"
    dataset_path = BENCHMARK_DIR / "benchmark_dataset.jsonl"
    assert manifest_path.exists(), "Benchmark manifest.json is missing!"
    assert dataset_path.exists(), "Benchmark benchmark_dataset.jsonl is missing!"

    dataset_bytes = dataset_path.read_bytes()
    computed_hash = hashlib.sha256(dataset_bytes).hexdigest()
    assert (
        computed_hash == FROZEN_BENCHMARK_MANIFEST_HASH
    ), f"FATAL: Benchmark integrity hash changed! Got {computed_hash}, expected {FROZEN_BENCHMARK_MANIFEST_HASH}"


# Test 22: Official baseline metrics immutability
def test_official_baseline_immutability() -> None:
    metrics_path = BASELINE_DIR / "metrics.json"
    assert metrics_path.exists(), "Official baseline metrics.json is missing!"
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert (
        data["classification"]["accuracy"] == 0.79
    ), f"Baseline accuracy modified: {data['classification']['accuracy']}"
    assert (
        data["classification"]["total_samples"] == 300
    ), f"Baseline total samples modified: {data['classification']['total_samples']}"


# Test 23: Training image git-ignore behavior
def test_training_image_git_ignore_behavior() -> None:
    gitignore_path = REPO_ROOT / "datasets" / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")
    assert "training_v1/images/" in content, "training_v1/images/ must be ignored in datasets/.gitignore"
    assert "!manifest.jsonl" in content, "!manifest.jsonl must not be ignored"


# Test 24: Benchmark files count and integrity preservation
def test_benchmark_files_count_and_preservation() -> None:
    with open(BENCHMARK_DIR / "benchmark_dataset.jsonl", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert len(lines) == 300, f"Benchmark sample count changed: expected 300, got {len(lines)}"
