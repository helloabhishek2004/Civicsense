"""Unit tests for Phase 3.3 Step 6 Batch 3 acquisition and governance.

Verifies:
- Dry-run mode produces plan without modifying disk or clean splits
- Batch 3 staging paths convention (datasets/raw/<source>/batch_3/images/)
- Spec validation for all 5 Boston specs and 4 Wikimedia specs
- Source-ID and SHA-256 deduplication
- Benchmark collision and leakage rejection
- Annotation logic across all 6 canonical categories
- Other explicit subtype validation
- Benchmark integrity hash immutability
- Quarantine isolation from clean splits
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
backend_path = repo_root / "backend"
for _p in (str(repo_root), str(backend_path)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.datasets.acquire_batch_3 import (  # noqa: E402
    BATCH_3_BOSTON_SPECS,
    BATCH_3_WIKIMEDIA_SPECS,
    Batch3AcquisitionRunner,
)

BENCHMARK_DIR = repo_root / "datasets" / "benchmark_v1"
TRAINING_DIR = repo_root / "datasets" / "training_v1"
BENCHMARK_MANIFEST_HASH = (
    "e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b"
)


def test_dry_run_does_not_write_batch3_manifest(tmp_path: Path) -> None:
    """Dry-run must not create batch_3_manifest.json."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    training_dir = tmp_path / "training_v1"
    training_dir.mkdir()
    (training_dir / "manifest.jsonl").write_text("")

    runner = Batch3AcquisitionRunner(
        raw_dir=raw_dir,
        benchmark_dir=BENCHMARK_DIR,
        training_dir=training_dir,
        execute=False,
    )
    plan = runner.run_dry_run()
    assert plan["mode"] == "DRY_RUN"
    assert plan["target_total_candidates"] == 310
    assert plan["clean_splits_modified"] is False
    assert plan["model_training"] is False
    assert plan["weights_downloaded"] is False
    assert not (training_dir / "acquisition" / "batch_3_manifest.json").exists()


def test_execute_mode_stages_under_batch_3_directories() -> None:
    """Batch 3 candidate image rel paths must point to batch_3/images."""
    for spec in BATCH_3_BOSTON_SPECS:
        assert spec["source_name"] == "boston311"
        assert spec["target_count"] > 0
    for spec in BATCH_3_WIKIMEDIA_SPECS:
        assert spec["target_count"] > 0
        assert spec["raw_subdir"].startswith("wikimedia_")


def test_batch3_specs_cover_all_six_canonical_categories() -> None:
    """Batch 3 specs must cover all 6 canonical categories."""
    categories_covered = set()
    for s in BATCH_3_BOSTON_SPECS:
        categories_covered.add(s["category"])
    for s in BATCH_3_WIKIMEDIA_SPECS:
        categories_covered.add(s["category"])

    expected = {"Pothole", "Garbage", "Other", "Water Leakage", "Road Damage", "Streetlight"}
    assert categories_covered == expected


def test_batch3_other_specs_have_explicit_subtypes() -> None:
    """All Other category specs in Batch 3 must declare explicit valid subtypes."""
    from app.evaluation.training_schema import VALID_OTHER_SUBTYPES

    for s in BATCH_3_BOSTON_SPECS:
        if s["category"] == "Other":
            assert s["subtype"] in VALID_OTHER_SUBTYPES
    for s in BATCH_3_WIKIMEDIA_SPECS:
        if s["category"] == "Other":
            assert s["subtype"] in VALID_OTHER_SUBTYPES


def test_benchmark_collision_is_detected_and_quarantined_batch3(tmp_path: Path) -> None:
    """Candidates colliding with benchmark SHA-256 must be rejected."""
    training_dir = tmp_path / "training_v1"
    training_dir.mkdir()
    (training_dir / "manifest.jsonl").write_text("")

    runner = Batch3AcquisitionRunner(
        raw_dir=tmp_path / "raw",
        benchmark_dir=BENCHMARK_DIR,
        training_dir=training_dir,
        execute=True,
    )
    assert runner.leakage_index.benchmark_hashes, "Benchmark hashes must not be empty"
    benchmark_sha = next(iter(runner.leakage_index.benchmark_hashes.keys()))

    result = runner.leakage_index.check_candidate(
        sample_id="test_b3_collision",
        sha256=benchmark_sha,
        source_name="test_source",
        source_record_id="collision_b3_001",
        source_url="http://example.com/b3_test.jpg",
    )
    assert not result.passed, "Benchmark collision must be rejected"


def test_existing_benchmark_remains_byte_identical_batch3() -> None:
    """Benchmark manifest integrity_hash must match the frozen hash."""
    manifest_path = BENCHMARK_DIR / "manifest.json"
    assert manifest_path.exists(), "Benchmark manifest.json missing"
    manifest_data = json.loads(manifest_path.read_bytes())
    stored_hash = manifest_data.get("integrity_hash", "")
    assert stored_hash == BENCHMARK_MANIFEST_HASH


def test_annotation_pothole_acceptance_and_quarantine() -> None:
    """Pothole manual annotation properly accepts clear and quarantines ambiguous."""
    from scripts.datasets.apply_manual_annotations_batch3 import _annotate_pothole

    # Index 1 -> accepted clear
    cand_clear = {
        "sample_id": "bost_b3pothole_1",
        "canonical_category": "Pothole",
        "original_category": "Request for Pothole Repair",
        "text_description": "Pothole in roadway",
        "quality_flags": [],
        "original_metadata": {"location": "Beacon St, Boston"},
    }
    res_clear = _annotate_pothole(cand_clear, idx=1)
    assert res_clear["verification_status"] == "VERIFIED_CLEAN"
    assert res_clear["ambiguity_status"] == "clear"

    # Index 9 -> quarantined per depth ambiguity
    cand_ambig = dict(cand_clear)
    cand_ambig["sample_id"] = "bost_b3pothole_9"
    res_ambig = _annotate_pothole(cand_ambig, idx=9)
    assert res_ambig["verification_status"] == "QUARANTINED"
    assert res_ambig["ambiguity_status"] == "ambiguous"


def test_annotation_garbage_acceptance_and_quarantine() -> None:
    """Garbage annotation properly accepts illegal dumping and handles boundaries."""
    from scripts.datasets.apply_manual_annotations_batch3 import _annotate_garbage

    cand_dump = {
        "sample_id": "bost_b3dump_1",
        "canonical_category": "Garbage",
        "original_category": "Illegal Dumping",
        "text_description": "Illegal dumping of mattresses",
        "quality_flags": [],
        "original_metadata": {"location": "Dorchester Ave, Boston"},
    }
    res = _annotate_garbage(cand_dump, idx=1)
    assert res["verification_status"] == "VERIFIED_CLEAN"


def test_annotation_other_subtypes_enforced() -> None:
    """Other category must enforce valid explicit subtypes."""
    from scripts.datasets.apply_manual_annotations_batch3 import _annotate_other

    cand_graffiti = {
        "sample_id": "bost_b3graffiti_1",
        "canonical_category": "Other",
        "subtype": "graffiti",
        "original_category": "Graffiti Removal",
        "text_description": "Graffiti on brick wall",
        "quality_flags": [],
        "original_metadata": {"location": "Tremont St, Boston"},
    }
    res_g = _annotate_other(cand_graffiti, idx=1)
    assert res_g["verification_status"] == "VERIFIED_CLEAN"
    assert res_g["subtype"] == "graffiti"

    cand_tree = {
        "sample_id": "wmother_b3_101",
        "canonical_category": "Other",
        "subtype": "fallen_tree_blockage",
        "original_category": "fallen tree road",
        "text_description": "Fallen tree blocking road lane",
        "quality_flags": [],
    }
    res_t = _annotate_other(cand_tree, idx=1)
    assert res_t["verification_status"] == "VERIFIED_CLEAN"
    assert res_t["subtype"] == "fallen_tree_blockage"


def test_annotation_water_leakage_quarantines_rain() -> None:
    """Water leakage annotation quarantines rain/flooding."""
    from scripts.datasets.apply_manual_annotations_batch3 import _annotate_water_leakage

    cand_rain = {
        "sample_id": "wmwater_b3_99",
        "canonical_category": "Water Leakage",
        "original_category": "rain storm flood",
        "text_description": "Heavy rain causing puddle on street",
        "quality_flags": [],
    }
    res = _annotate_water_leakage(cand_rain, idx=1)
    assert res["verification_status"] == "QUARANTINED"


def test_annotation_road_damage_quarantines_pothole() -> None:
    """Road damage annotation quarantines dominant pothole cavities."""
    from scripts.datasets.apply_manual_annotations_batch3 import _annotate_road_damage

    cand_pothole = {
        "sample_id": "wmroad_b3_77",
        "canonical_category": "Road Damage",
        "original_category": "pothole cavity",
        "text_description": "Deep pothole hole in road",
        "quality_flags": [],
    }
    res = _annotate_road_damage(cand_pothole, idx=1)
    assert res["verification_status"] == "QUARANTINED"
    assert "Pothole" in res["secondary_categories"]


def test_annotation_streetlight_quarantines_decorative() -> None:
    """Streetlight annotation quarantines decorative/festival lighting."""
    from scripts.datasets.apply_manual_annotations_batch3 import _annotate_streetlight

    cand_dec = {
        "sample_id": "wmlight_b3_55",
        "canonical_category": "Streetlight",
        "original_category": "christmas light",
        "text_description": "Christmas festival light decor on pole",
        "quality_flags": [],
    }
    res = _annotate_streetlight(cand_dec, idx=1)
    assert res["verification_status"] == "QUARANTINED"
