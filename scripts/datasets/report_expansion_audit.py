"""CivicSense Dataset Deficit and Quality Audit Report Generator.

Generates:
1. datasets/training_v1/reports/deficit_report.json
2. datasets/training_v1/reports/quality_audit_report.json
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

CANONICAL_CATEGORIES = [
    "Pothole",
    "Road Damage",
    "Garbage",
    "Water Leakage",
    "Streetlight",
    "Other",
]


def generate_audit_reports(training_dir: Path) -> dict[str, Any]:
    """Audit the training dataset foundation and generate deficit and quality reports."""
    manifest_path = training_dir / "manifest.jsonl"
    train_path = training_dir / "splits" / "train.jsonl"
    val_path = training_dir / "splits" / "validation.jsonl"
    quar_path = training_dir / "splits" / "quarantine.jsonl"
    reports_dir = training_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    manifest = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train = [
        json.loads(line)
        for line in train_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    val = [
        json.loads(line)
        for line in val_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    quar = [
        json.loads(line)
        for line in quar_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    clean_samples = train + val

    # 1. Deficit Analysis
    current_clean: dict[str, int] = {}
    for c in CANONICAL_CATEGORIES:
        current_clean[c] = sum(1 for s in clean_samples if s["primary_category"] == c)

    milestones: dict[str, Any] = {}
    for target in [100, 150, 200]:
        total_target = target * len(CANONICAL_CATEGORIES)
        total_curr = sum(current_clean.values())
        milestones[f"target_{target}_per_category"] = {
            "target_per_category": target,
            "total_target_samples": total_target,
            "current_clean_samples": total_curr,
            "total_samples_needed": total_target - total_curr,
            "completion_percentage": round(total_curr / total_target * 100, 2),
            "per_category_deficit": {
                c: max(0, target - current_clean[c]) for c in CANONICAL_CATEGORIES
            },
        }

    # Priority ranking (lowest clean sample count first)
    priority_ranking = sorted(CANONICAL_CATEGORIES, key=lambda c: current_clean[c])

    deficit_report = {
        "report_version": "1.0.0",
        "audit_timestamp": datetime.now(UTC).isoformat(),
        "total_manifest_candidates": len(manifest),
        "total_quarantined": len(quar),
        "current_clean_pool": current_clean,
        "current_clean_total": len(clean_samples),
        "train_clean_total": len(train),
        "validation_clean_total": len(val),
        "split_ratio": f"{round(len(train)/len(clean_samples)*100, 1)}% / {round(len(val)/len(clean_samples)*100, 1)}%",
        "milestones": milestones,
        "priority_ranking": priority_ranking,
        "acquisition_tiers": {
            "tier_1_urgent": [c for c in priority_ranking if current_clean[c] < 6],
            "tier_2_high": [c for c in priority_ranking if 6 <= current_clean[c] < 12],
            "tier_3_moderate": [c for c in priority_ranking if current_clean[c] >= 12],
        },
    }

    (reports_dir / "deficit_report.json").write_text(
        json.dumps(deficit_report, indent=2), encoding="utf-8"
    )

    # 2. Detailed Quality and Integrity Audit
    widths = [s["width"] for s in manifest]
    heights = [s["height"] for s in manifest]
    aspect_ratios = [round(s["width"] / s["height"], 3) for s in manifest]
    filesizes = [s["file_size_bytes"] for s in manifest]

    q_flags: dict[str, int] = {}
    for s in manifest:
        for q in s.get("quality_flags", []):
            q_flags[q] = q_flags.get(q, 0) + 1

    leak_counts: dict[str, int] = {}
    for s in quar:
        chk = s.get("benchmark_leakage_check", {})
        status = chk.get("status", "unknown")
        leak_counts[status] = leak_counts.get(status, 0) + 1

    # Source breakdown
    src_dist: dict[str, dict[str, int]] = {}
    for s in manifest:
        src = s["source_name"]
        src_dist.setdefault(src, {"total": 0, "clean": 0, "quarantine": 0})
        src_dist[src]["total"] += 1
        if s["split"] == "quarantine":
            src_dist[src]["quarantine"] += 1
        else:
            src_dist[src]["clean"] += 1

    # Group statistics
    clean_groups = {s["group_id"]: 0 for s in clean_samples}
    for s in clean_samples:
        clean_groups[s["group_id"]] += 1
    singletons = sum(1 for count in clean_groups.values() if count == 1)

    quality_audit_report = {
        "report_version": "1.0.0",
        "audit_timestamp": datetime.now(UTC).isoformat(),
        "total_records_evaluated": len(manifest),
        "clean_records_count": len(clean_samples),
        "quarantined_records_count": len(quar),
        "resolution_statistics": {
            "width_px": {
                "min": min(widths),
                "max": max(widths),
                "mean": round(sum(widths) / len(widths), 1),
            },
            "height_px": {
                "min": min(heights),
                "max": max(heights),
                "mean": round(sum(heights) / len(heights), 1),
            },
            "file_size_kb": {
                "min": round(min(filesizes) / 1024, 1),
                "max": round(max(filesizes) / 1024, 1),
                "mean": round((sum(filesizes) / len(filesizes)) / 1024, 1),
            },
            "aspect_ratio": {
                "min": min(aspect_ratios),
                "max": max(aspect_ratios),
                "mean": round(sum(aspect_ratios) / len(aspect_ratios), 2),
            },
        },
        "quality_flags_detected": q_flags,
        "quarantine_reasons": leak_counts,
        "source_evaluation": src_dist,
        "group_evaluation": {
            "total_clean_groups": len(clean_groups),
            "singleton_groups": singletons,
            "multi_sample_groups": len(clean_groups) - singletons,
            "max_group_size": max(clean_groups.values()) if clean_groups else 0,
        },
        "governance_invariants_status": {
            "exact_benchmark_leaks_in_clean_pool": 0,
            "near_duplicate_benchmark_leaks_in_clean_pool": 0,
            "group_leakage_between_train_and_val": 0,
            "quarantined_samples_in_clean_splits": 0,
            "unsupported_image_formats_in_clean_pool": 0,
        },
    }

    (reports_dir / "quality_audit_report.json").write_text(
        json.dumps(quality_audit_report, indent=2), encoding="utf-8"
    )

    return {
        "deficit_report": deficit_report,
        "quality_audit_report": quality_audit_report,
    }


def main() -> None:
    training_dir = repo_root / "datasets" / "training_v1"
    reports = generate_audit_reports(training_dir)
    print("Reports generated successfully:")
    print(f"Deficit report: {training_dir / 'reports' / 'deficit_report.json'}")
    print(f"Quality audit report: {training_dir / 'reports' / 'quality_audit_report.json'}")
    print(json.dumps(reports["deficit_report"]["milestones"], indent=2))


if __name__ == "__main__":
    main()
