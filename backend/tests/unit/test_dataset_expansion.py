"""CivicSense Dataset Expansion, Quality Audit, and Deficit Analysis Tests.

Tests:
1. Deficit calculation math for targets (100, 150, 200 per category)
2. Deficit priority ranking identifies lowest-count categories first
3. Pre-download leakage check catches benchmark record IDs before network fetching
4. Post-download leakage check catches benchmark dHash near-duplicates
5. Quality audit report generates required metrics
6. Controlled expansion runner defaults to DRY-RUN mode
7. Quality gates evaluation logic
8. Source registry compliance across candidate sources
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from scripts.datasets.controlled_expansion import ControlledExpansionRunner
from scripts.datasets.leakage_detector import BenchmarkLeakageIndex
from scripts.datasets.report_expansion_audit import generate_audit_reports
from scripts.datasets.source_registry import get_source

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_DIR = REPO_ROOT / "datasets" / "benchmark_v1"
TRAINING_DIR = REPO_ROOT / "datasets" / "training_v1"


def test_deficit_calculation_and_targets() -> None:
    reports = generate_audit_reports(TRAINING_DIR)
    deficit_rep = reports["deficit_report"]

    milestones = deficit_rep["milestones"]
    assert "target_100_per_category" in milestones
    assert "target_150_per_category" in milestones
    assert "target_200_per_category" in milestones

    t100 = milestones["target_100_per_category"]
    assert t100["total_target_samples"] == 600
    expected_needed_100 = 600 - deficit_rep["current_clean_total"]
    assert t100["total_samples_needed"] == expected_needed_100
    expected_pct = round((deficit_rep["current_clean_total"] / 600) * 100, 2)
    assert t100["completion_percentage"] == expected_pct

    t200 = milestones["target_200_per_category"]
    assert t200["total_target_samples"] == 1200
    expected_needed_200 = 1200 - deficit_rep["current_clean_total"]
    assert t200["total_samples_needed"] == expected_needed_200


def test_priority_ranking_identifies_weakest_categories() -> None:
    reports = generate_audit_reports(TRAINING_DIR)
    deficit_rep = reports["deficit_report"]

    ranking = deficit_rep["priority_ranking"]
    assert len(ranking) == 6
    # Categories must be strictly ordered from lowest to highest clean counts
    counts = deficit_rep["current_clean_pool"]
    for i in range(len(ranking) - 1):
        assert counts[ranking[i]] <= counts[ranking[i + 1]]
    assert "tier_1_urgent" in deficit_rep["acquisition_tiers"]


def test_pre_download_leakage_check_catches_benchmark_ids() -> None:
    leakage_index = BenchmarkLeakageIndex(BENCHMARK_DIR)
    # Get a real benchmark source ID
    (src_name, src_rec) = list(leakage_index.benchmark_source_ids.keys())[0]

    # Check candidate before download (empty SHA-256 and dHash)
    res = leakage_index.check_candidate(
        sample_id=f"test_{src_rec}",
        sha256="",
        source_name=src_name,
        source_record_id=src_rec,
    )
    assert res.passed is False
    assert res.status == "FAILED_SOURCE_ID"


def test_post_download_leakage_check_catches_near_duplicate() -> None:
    leakage_index = BenchmarkLeakageIndex(BENCHMARK_DIR)
    real_bm_dhash = leakage_index.benchmark_dhashes[0][1]

    # dHash with distance 2
    altered_val = int(real_bm_dhash, 16) ^ 0b11
    near_dup_dhash = f"{altered_val:016x}"

    res = leakage_index.check_candidate(
        sample_id="test_post_download",
        sha256="9" * 64,
        source_name="new_source",
        source_record_id="unique_9999",
        dhash=near_dup_dhash,
    )
    assert res.passed is False
    assert res.status == "FAILED_DHASH_NEAR_DUPLICATE"


def test_quality_audit_report_contains_governance_invariants() -> None:
    reports = generate_audit_reports(TRAINING_DIR)
    q_rep = reports["quality_audit_report"]

    invariants = q_rep["governance_invariants_status"]
    assert invariants["exact_benchmark_leaks_in_clean_pool"] == 0
    assert invariants["near_duplicate_benchmark_leaks_in_clean_pool"] == 0
    assert invariants["group_leakage_between_train_and_val"] == 0
    assert invariants["quarantined_samples_in_clean_splits"] == 0


def test_controlled_expansion_runner_dry_run_safety() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = ControlledExpansionRunner(
            raw_dir=Path(tmpdir),
            benchmark_dir=BENCHMARK_DIR,
            execute=False,  # DRY RUN
        )
        plan = runner.acquire_boston311_candidates("Pothole", limit=5)
        assert plan["mode"] == "DRY_RUN"
        assert plan["acquired_count"] == 0
        assert plan["target_limit"] == 5


def test_quality_gates_evaluation() -> None:
    reports = generate_audit_reports(TRAINING_DIR)
    deficit_rep = reports["deficit_report"]
    quality_rep = reports["quality_audit_report"]

    clean_total = deficit_rep["current_clean_total"]
    # Gate 1 (300 pilot gate): Now successfully reached (333 clean samples)
    gate_300_met = clean_total >= 300
    assert gate_300_met is True

    # Gate 2 (1,200 production gate): Not yet met
    gate_1200_met = clean_total >= 1200
    assert gate_1200_met is False

    # Invariants gates: Must be met
    assert quality_rep["governance_invariants_status"]["exact_benchmark_leaks_in_clean_pool"] == 0
    assert quality_rep["governance_invariants_status"]["group_leakage_between_train_and_val"] == 0


def test_source_registry_documentation_completeness() -> None:
    for src_id in ["boston311", "taco", "wikimedia_water", "wikimedia_streetlight", "wikimedia_road_damage"]:
        meta = get_source(src_id)
        assert meta is not None, f"Source {src_id} missing from registry!"
        assert meta.official_url.startswith("http")
        assert len(meta.license) > 0
        assert meta.license_verified is True
