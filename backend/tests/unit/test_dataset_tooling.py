import io
import json
from pathlib import Path

from PIL import Image

from scripts.datasets.curate_benchmark import curate_benchmark
from scripts.datasets.deduplicate_benchmark import (
    deduplicate_exact,
    deduplicate_perceptual,
)
from scripts.datasets.download_subsets import run_download_pipeline
from scripts.datasets.normalize_annotations import (
    MappingOutcome,
    filter_taco_image_license,
    normalize_annotation,
)
from scripts.datasets.report_dataset import generate_dataset_report
from scripts.datasets.source_registry import get_source, list_sources
from scripts.datasets.validate_images import validate_image_file


def _make_test_jpeg_bytes(
    size: tuple[int, int] = (100, 100),
    color: str = "blue",
    pattern_id: int = 0,
) -> bytes:
    """Generate in-memory valid JPEG image bytes with distinct patterns."""
    buf = io.BytesIO()
    if pattern_id == 1:
        img = Image.new("L", size, 255)
        for x in range(size[0] // 2):
            for y in range(size[1]):
                img.putpixel((x, y), 0)
    elif pattern_id == 2:
        img = Image.new("L", size, 0)
        for x in range(size[0] // 3, (2 * size[0]) // 3):
            for y in range(size[1]):
                img.putpixel((x, y), 255)
    elif pattern_id == 3:
        img = Image.new("L", size, 0)
        for x in range(size[0]):
            val = int((x / max(1, size[0] - 1)) * 255)
            for y in range(size[1]):
                img.putpixel((x, y), val)
    else:
        img = Image.new("RGB", size, color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ===========================================================================
# 1. SOURCE REGISTRY TESTS
# ===========================================================================


def test_source_registry_lookup_and_fields() -> None:
    """Source registry contains verified descriptors for all target candidates."""
    sources = list_sources()
    assert len(sources) >= 4

    rdd = get_source("rdd2022")
    assert rdd is not None
    assert "CC-BY-NC-3.0" in rdd.license
    assert "Pothole" in rdd.candidate_categories
    assert rdd.download_policy == "manual_prerequisite"

    taco = get_source("taco")
    assert taco is not None
    assert "Garbage" in taco.candidate_categories
    assert taco.download_policy == "subset_download"

    boston = get_source("boston311")
    assert boston is not None
    assert "Streetlight" in boston.candidate_categories
    assert "Water Leakage" in boston.candidate_categories

    nyc = get_source("nyc311")
    assert nyc is not None
    assert nyc.download_policy == "metadata_only"

    # Unknown source returns None
    assert get_source("unknown_source_xyz") is None


# ===========================================================================
# 2. ANNOTATION NORMALIZATION TESTS
# ===========================================================================


def test_canonical_mapping_accepted_labels() -> None:
    """Known source labels map cleanly to canonical CivicSense categories."""
    # RDD2022
    rdd_pothole = normalize_annotation(
        source_dataset="rdd2022",
        source_record_id="rec-01",
        original_category="D40",
    )
    assert rdd_pothole.outcome == MappingOutcome.ACCEPTED
    assert rdd_pothole.canonical_category == "Pothole"

    rdd_crack = normalize_annotation(
        source_dataset="rdd2022",
        source_record_id="rec-02",
        original_category="D20",
    )
    assert rdd_crack.outcome == MappingOutcome.ACCEPTED
    assert rdd_crack.canonical_category == "Road Damage"

    # TACO
    taco_bottle = normalize_annotation(
        source_dataset="taco",
        source_record_id="rec-03",
        original_category="Plastic bottle",
    )
    assert taco_bottle.outcome == MappingOutcome.ACCEPTED
    assert taco_bottle.canonical_category == "Garbage"

    # Boston 311
    b_pothole = normalize_annotation(
        source_dataset="boston311",
        source_record_id="rec-04",
        original_category="Request for Pothole Repair",
    )
    assert b_pothole.outcome == MappingOutcome.ACCEPTED
    assert b_pothole.canonical_category == "Pothole"

    b_water = normalize_annotation(
        source_dataset="boston311",
        source_record_id="rec-05",
        original_category="Broken Water Main",
    )
    assert b_water.outcome == MappingOutcome.ACCEPTED
    assert b_water.canonical_category == "Water Leakage"

    b_light = normalize_annotation(
        source_dataset="boston311",
        source_record_id="rec-06",
        original_category="Street Light Outage",
    )
    assert b_light.outcome == MappingOutcome.ACCEPTED
    assert b_light.canonical_category == "Streetlight"


def test_unknown_and_ambiguous_label_rejection() -> None:
    """Ambiguous or out-of-domain labels are rejected or routed to manual review."""
    # RDD2022 line blur (painting, not road structural damage)
    rdd_paint = normalize_annotation(
        source_dataset="rdd2022",
        source_record_id="rec-07",
        original_category="D43",
    )
    assert rdd_paint.outcome == MappingOutcome.REJECTED
    assert rdd_paint.canonical_category is None

    # TACO background
    taco_bg = normalize_annotation(
        source_dataset="taco",
        source_record_id="rec-08",
        original_category="unlabeled",
    )
    assert taco_bg.outcome == MappingOutcome.REJECTED

    # Boston 311 ambiguous general request
    b_ambig = normalize_annotation(
        source_dataset="boston311",
        source_record_id="rec-09",
        original_category="General Request",
    )
    assert b_ambig.outcome == MappingOutcome.MANUAL_REVIEW
    assert b_ambig.canonical_category is None

    # Completely unknown source
    unknown_src = normalize_annotation(
        source_dataset="fantasy_dataset",
        source_record_id="rec-10",
        original_category="some_tag",
    )
    assert unknown_src.outcome == MappingOutcome.REJECTED


# ===========================================================================
# 3. IMAGE VALIDATION TESTS
# ===========================================================================


def test_image_validation_valid_jpeg(tmp_path: Path) -> None:
    """Valid JPEG passes validation with correct dimensions and hashes."""
    img_bytes = _make_test_jpeg_bytes(size=(128, 128), color="green")
    img_file = tmp_path / "valid.jpg"
    img_file.write_bytes(img_bytes)

    res = validate_image_file(img_file, base_dir=tmp_path)
    assert res.is_valid is True
    assert res.mime_type == "image/jpeg"
    assert res.width == 128
    assert res.height == 128
    assert len(res.sha256) == 64
    assert len(res.phash) == 16


def test_image_validation_corrupt_and_missing(tmp_path: Path) -> None:
    """Corrupt bytes and non-existent files fail validation with explicit reasons."""
    # Corrupt image
    corrupt_file = tmp_path / "corrupt.jpg"
    corrupt_file.write_bytes(b"NOT_A_REAL_IMAGE_BYTES")
    res_corrupt = validate_image_file(corrupt_file, base_dir=tmp_path)
    assert res_corrupt.is_valid is False
    assert "Unsupported magic bytes" in str(res_corrupt.rejection_reason)

    # Missing image
    missing_file = tmp_path / "missing.jpg"
    res_missing = validate_image_file(missing_file, base_dir=tmp_path)
    assert res_missing.is_valid is False
    assert "File does not exist" in str(res_missing.rejection_reason)


def test_image_validation_path_traversal(tmp_path: Path) -> None:
    """Attempting path traversal outside base directory is rejected."""
    safe_dir = tmp_path / "safe"
    safe_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    outside_file = outside_dir / "target.jpg"
    outside_file.write_bytes(_make_test_jpeg_bytes())

    # Validate with base_dir constrained to safe_dir
    res = validate_image_file(outside_file, base_dir=safe_dir)
    assert res.is_valid is False
    assert "Path traversal violation" in str(res.rejection_reason)


# ===========================================================================
# 4. DEDUPLICATION TESTS
# ===========================================================================


def test_exact_duplicate_detection() -> None:
    """Exact duplicates sharing the same SHA-256 are detected and flagged."""
    samples = [
        {"sample_id": "sample-01", "sha256": "hash_aaa", "canonical_category": "Pothole"},
        {"sample_id": "sample-02", "sha256": "hash_bbb", "canonical_category": "Garbage"},
        {"sample_id": "sample-03", "sha256": "hash_aaa", "canonical_category": "Pothole"},
    ]

    unique, duplicates = deduplicate_exact(samples)
    assert len(unique) == 2
    assert len(duplicates) == 1
    assert duplicates[0]["sample_id"] == "sample-03"
    assert duplicates[0]["duplicate_group_id"] == "sample-01"


def test_near_duplicate_detection_dhash() -> None:
    """Near duplicates with Hamming distance <= threshold are flagged."""
    # Hash 1: 0000000000000000
    # Hash 2: 0000000000000003 (2 bits different -> near duplicate)
    # Hash 3: ffffffffffffffff (64 bits different -> distinct)
    samples = [
        {"sample_id": "sample-01", "phash": "0000000000000000", "sha256": "h1"},
        {"sample_id": "sample-02", "phash": "0000000000000003", "sha256": "h2"},
        {"sample_id": "sample-03", "phash": "ffffffffffffffff", "sha256": "h3"},
    ]

    unique, duplicates = deduplicate_perceptual(samples, threshold=4)
    assert len(unique) == 2
    assert len(duplicates) == 1
    assert duplicates[0]["sample_id"] == "sample-02"
    assert duplicates[0]["duplicate_group_id"] == "sample-01"


# ===========================================================================
# 5. BENCHMARK CURATION & BALANCE TESTS
# ===========================================================================


def test_curate_benchmark_shortage_preservation_and_no_fabrication(tmp_path: Path) -> None:
    """When category count is under target (e.g. 2 vs 50), actual count is retained."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    img1 = images_dir / "p1.jpg"
    img1.write_bytes(_make_test_jpeg_bytes(size=(64, 64), pattern_id=1))

    img2 = images_dir / "p2.jpg"
    img2.write_bytes(_make_test_jpeg_bytes(size=(64, 64), pattern_id=2))

    img3 = images_dir / "g1.jpg"
    img3.write_bytes(_make_test_jpeg_bytes(size=(64, 64), pattern_id=3))

    candidates = [
        {
            "sample_id": "pothole-01",
            "image_rel_path": "p1.jpg",
            "source_dataset": "rdd2022",
            "source_record_id": "rdd-01",
            "original_category": "D40",
            "license": "CC-BY-SA-4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": "RDD2022 team",
        },
        {
            "sample_id": "pothole-02",
            "image_rel_path": "p2.jpg",
            "source_dataset": "rdd2022",
            "source_record_id": "rdd-02",
            "original_category": "pothole",
            "license": "CC-BY-SA-4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": "RDD2022 team",
        },
        {
            "sample_id": "garbage-01",
            "image_rel_path": "g1.jpg",
            "source_dataset": "taco",
            "source_record_id": "taco-01",
            "original_category": "bottle",
            "license": "CC-BY-SA-4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": "TACO team",
        },
    ]

    out_dir = tmp_path / "benchmark_out"
    report = curate_benchmark(
        candidate_records=candidates,
        images_root=images_dir,
        output_dir=out_dir,
        target_per_category=50,
    )

    # Exactly 3 samples selected - NO synthetic duplication to reach 50!
    assert report["total_selected"] == 3
    assert report["category_counts"]["Pothole"] == 2
    assert report["category_counts"]["Garbage"] == 1
    assert report["category_counts"]["Water Leakage"] == 0
    assert report["category_shortages"]["Pothole"] == 48
    assert report["category_shortages"]["Garbage"] == 49
    assert report["category_shortages"]["Water Leakage"] == 50

    # Verify JSONL lines match exactly 3 records
    jsonl_file = out_dir / "benchmark_dataset.jsonl"
    assert jsonl_file.exists()
    lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3

    # Verify manifest
    manifest_file = out_dir / "manifest.json"
    assert manifest_file.exists()
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest_data["total_sample_count"] == 3


# ===========================================================================
# 6. DOWNLOAD SUBSETS DRY-RUN TESTS
# ===========================================================================


def test_download_subsets_dry_run(tmp_path: Path) -> None:
    """Download pipeline in default mode executes dry-run without downloading data."""
    raw_dir = tmp_path / "raw"
    res = run_download_pipeline(
        source_name="all",
        output_dir=raw_dir,
        limit=20,
        execute=False,  # Dry run
    )

    assert res["execute_mode"] is False
    manifest_path = Path(res["manifest_path"])
    assert manifest_path.exists()

    manifest_entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest_entries) >= 4

    for entry in manifest_entries:
        assert entry["status"] == "DRY_RUN_METADATA_ONLY"
        assert entry["downloaded_count"] == 0
        assert entry["total_bytes"] == 0


# ===========================================================================
# 7. QUALITY AND BALANCE REPORT TESTS
# ===========================================================================


def test_report_dataset_generation(tmp_path: Path) -> None:
    """Quality reporting tool aggregates dataset balance and shortages correctly."""
    sample = {
        "sample_id": "test-samp-01",
        "image_rel_path": "images/test.jpg",
        "source_dataset": "rdd2022",
        "source_record_id": "rec-1",
        "canonical_category": "Pothole",
        "original_category": "D40",
        "category_confidence": 1.0,
        "bounding_boxes": [],
        "text_description": "Road surface defect",
        "split": "benchmark",
        "license": "CC-BY-SA-4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "attribution": "Test",
        "is_blurry": False,
        "is_low_res": False,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "phash": "0000000000000000",
        "duplicate_group_id": None,
        "review_status": "CONFIRMED",
        "metadata_json": {},
    }
    jsonl_file = tmp_path / "benchmark_dataset.jsonl"
    jsonl_file.write_text(json.dumps(sample) + "\n", encoding="utf-8")

    out_json = tmp_path / "report.json"
    rep = generate_dataset_report(jsonl_file, output_report_file=out_json)

    assert rep["total_samples"] == 1
    assert rep["category_distribution"]["Pothole"] == 1
    assert rep["category_shortages"]["Pothole"] == 49
    assert rep["is_balanced_at_target"] is False
    assert out_json.exists()


def test_filter_taco_image_license() -> None:
    """TACO license filter strictly rejects null and unspecified CC, accepts ODbL and CC-BY."""
    # Null / empty
    valid, reason = filter_taco_image_license(None)
    assert not valid
    assert "EXCLUDED_LICENSE_NULL" in reason

    valid, reason = filter_taco_image_license("")
    assert not valid
    assert "EXCLUDED_LICENSE_NULL" in reason

    # Unspecified "CC"
    valid, reason = filter_taco_image_license("CC")
    assert not valid
    assert "EXCLUDED_UNSPECIFIED_CC" in reason

    # Verified ODbL OpenLitterMap
    valid, label = filter_taco_image_license("ODBL (c) OpenLitterMap & Contributors")
    assert valid
    assert "ODbL" in label

    # Verified CC-BY
    valid, label = filter_taco_image_license("CC-BY 4.0")
    assert valid

    # Public domain
    valid, label = filter_taco_image_license("Public Domain")
    assert valid

    # Unknown unverified license
    valid, reason = filter_taco_image_license("All Rights Reserved - Random Site")
    assert not valid
    assert "EXCLUDED_UNKNOWN_LICENSE" in reason


def test_wikimedia_water_normalization() -> None:
    """Wikimedia Commons water leakage annotations normalize to Water Leakage under open license."""
    norm_accepted = normalize_annotation(
        source_dataset="wikimedia_water",
        source_record_id="50718963",
        original_category="burst water main",
        text_description="Burst pipe flooding the street",
        source_license="CC BY-SA 4.0",
    )
    assert norm_accepted.outcome == MappingOutcome.ACCEPTED
    assert norm_accepted.canonical_category == "Water Leakage"

    norm_unverified_lic = normalize_annotation(
        source_dataset="wikimedia_water",
        source_record_id="50718964",
        original_category="burst water main",
        text_description="Burst pipe",
        source_license="proprietary",
    )
    assert norm_unverified_lic.outcome == MappingOutcome.MANUAL_REVIEW

    norm_irrelevant = normalize_annotation(
        source_dataset="wikimedia_water",
        source_record_id="50718965",
        original_category="sunny sky",
        text_description="Blue sky above city",
        source_license="CC BY-SA 4.0",
    )
    assert norm_irrelevant.outcome == MappingOutcome.REJECTED


def test_validate_image_decompression_bomb_safety(tmp_path: Path) -> None:
    """Image validator safely flags decompression bombs without unhandled exceptions."""
    bomb_file = tmp_path / "bomb.jpg"
    # Create image with header claiming excessive size or dimensions
    img = Image.new("RGB", (6000, 5000), color="white")
    img.save(bomb_file, format="JPEG")
    res = validate_image_file(bomb_file)
    # 6000 * 5000 = 30,000,000 > MAX_IMAGE_PIXELS (25,000,000)
    assert not res.is_valid
    assert "Decompression bomb" in (res.rejection_reason or "")


def test_wikimedia_streetlight_and_road_damage_normalization() -> None:
    """Wikimedia streetlight and road damage annotations normalize to canonical categories."""
    # Streetlight accepted
    norm_light = normalize_annotation(
        source_dataset="wikimedia_streetlight",
        source_record_id="12345",
        original_category="broken street light",
        text_description="Damaged lamp post in residential street",
        source_license="CC BY-SA 4.0",
    )
    assert norm_light.outcome == MappingOutcome.ACCEPTED
    assert norm_light.canonical_category == "Streetlight"

    # Road damage accepted
    norm_road = normalize_annotation(
        source_dataset="wikimedia_road_damage",
        source_record_id="67890",
        original_category="alligator cracking road",
        text_description="Asphalt fatigue cracking on municipal roadway",
        source_license="CC BY 3.0",
    )
    assert norm_road.outcome == MappingOutcome.ACCEPTED
    assert norm_road.canonical_category == "Road Damage"

    # Unverified license rejected to manual review
    norm_bad_lic = normalize_annotation(
        source_dataset="wikimedia_streetlight",
        source_record_id="99999",
        original_category="street lamp",
        text_description="Lamp post",
        source_license="All Rights Reserved",
    )
    assert norm_bad_lic.outcome == MappingOutcome.MANUAL_REVIEW


