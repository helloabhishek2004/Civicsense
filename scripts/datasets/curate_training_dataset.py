"""CivicSense Training Dataset Curation & Processing Pipeline.

Orchestrates the preparation of datasets/training_v1/:
1. Ingestion of candidate samples from raw datasets.
2. Image integrity and quality validation (magic bytes, dimensions, SHA-256, dHash).
3. Leakage detection against the frozen evaluation benchmark (datasets/benchmark_v1/).
4. Intra-dataset duplicate and near-duplicate detection.
5. Auditable incident group ID assignment.
6. Deterministic group-level train/validation/quarantine splitting.
7. Emission of manifests, split JSONL files, summary, and audit reports.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure repository root and backend are on sys.path
repo_root = Path(__file__).resolve().parents[2]
backend_path = repo_root / "backend"
for p in (str(repo_root), str(backend_path)):
    if p not in sys.path:
        sys.path.insert(0, p)


from app.evaluation.training_schema import (  # noqa: E402
    CANONICAL_CATEGORIES,
    AmbiguityStatus,
    LeakageStatus,
    LicenseScope,
    TrainingDatasetSummary,
    TrainingSample,
    TrainingSplit,
    VerificationMethod,
)
from scripts.datasets.leakage_detector import BenchmarkLeakageIndex  # noqa: E402
from scripts.datasets.source_registry import DATASET_REGISTRY, get_source  # noqa: E402
from scripts.datasets.training_splitter import (  # noqa: E402
    assign_group_ids,
    detect_intra_dataset_duplicates,
    split_training_dataset,
)
from scripts.datasets.validate_images import validate_image_file  # noqa: E402


def normalize_category_label(cat_raw: str | None) -> str:
    """Map raw category to canonical 6 CivicSense categories."""
    if not cat_raw:
        return "Other"
    if cat_raw in CANONICAL_CATEGORIES:
        return cat_raw
    val = cat_raw.strip().lower()
    if "pothole" in val:
        return "Pothole"
    elif "road" in val or "sidewalk" in val or "crack" in val or "pavement" in val:
        return "Road Damage"
    elif "garbage" in val or "trash" in val or "dumping" in val or "litter" in val or "debris" in val:
        return "Garbage"
    elif "water" in val or "leak" in val or "pipe" in val or "hydrant" in val or "flood" in val:
        return "Water Leakage"
    elif "streetlight" in val or "light" in val or "lamp" in val:
        return "Streetlight"
    return "Other"


def curate_training_pipeline(
    raw_dir: Path,
    benchmark_dir: Path,
    output_dir: Path,
    train_ratio: float = 0.8,
    seed: int = 42,
) -> dict[str, Any]:
    """Execute complete curation pipeline and write all output artifacts."""
    output_dir = Path(output_dir)
    splits_dir = output_dir / "splits"
    reports_dir = output_dir / "reports"
    prov_dir = output_dir / "provenance"

    splits_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    prov_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initialize Benchmark Leakage Detector
    leakage_index = BenchmarkLeakageIndex(benchmark_dir)

    # 2. Gather candidate raw samples
    candidate_raw_list: list[dict[str, Any]] = []
    for sub in sorted(raw_dir.iterdir()):
        if sub.is_dir():
            raw_samples_file = sub / "raw_samples.json"
            if raw_samples_file.exists():
                try:
                    data = json.loads(raw_samples_file.read_text(encoding="utf-8"))
                    for item in data:
                        # Normalize source dataset name
                        if "source_name" not in item:
                            item["source_name"] = item.get("source_dataset", sub.name)
                        candidate_raw_list.append(item)
                except Exception as err:
                    print(f"Warning: Failed to load {raw_samples_file}: {err}")

    # 3. Image validation, hashing, and quality assessment
    validated_candidates: list[dict[str, Any]] = []
    quality_report_items: list[dict[str, Any]] = []

    for raw in candidate_raw_list:
        raw_id = str(raw.get("sample_id") or raw.get("source_record_id") or f"cand_{len(validated_candidates)}")
        sub_name = str(raw.get("source_name", raw.get("source_dataset", "")))
        local_p_str = str(raw.get("local_path") or raw.get("image_rel_path") or "")

        img_path = Path(local_p_str)
        if not img_path.is_absolute():
            if (raw_dir / local_p_str).exists():
                img_path = raw_dir / local_p_str
            elif (raw_dir / sub_name / local_p_str).exists():
                img_path = raw_dir / sub_name / local_p_str
            elif (repo_root / local_p_str).exists():
                img_path = repo_root / local_p_str
            else:
                img_path = raw_dir / local_p_str

        # Image file validation
        val_res = validate_image_file(img_path)
        quality_flags: list[str] = list(val_res.warnings)
        if val_res.is_blurry:
            quality_flags.append("is_blurry")
        if val_res.is_low_res:
            quality_flags.append("is_low_res")


        quality_report_items.append({
            "sample_id": raw_id,
            "path": str(img_path),
            "is_valid": val_res.is_valid,
            "rejection_reason": val_res.rejection_reason,
            "quality_flags": quality_flags,
            "dimensions": f"{val_res.width}x{val_res.height}",
            "file_size": val_res.file_size_bytes,
        })

        try:
            rel_path = img_path.relative_to(repo_root)
            computed_local_path = str(rel_path).replace("\\", "/")
        except Exception:
            computed_local_path = local_p_str.replace("\\", "/").lstrip("./") or f"datasets/quarantine/{raw_id}.jpg"

        src_name = str(raw.get("source_name", "unknown"))
        src_meta = get_source(src_name)
        resolved_license = raw.get("license") or (src_meta.license if src_meta else "Open Access")
        resolved_license_url = raw.get("license_url") or (src_meta.license_url if src_meta else None)
        resolved_source_url = raw.get("source_url") or raw.get("url") or (src_meta.official_url if src_meta else "https://civicsense.local")
        resolved_rec_id = str(raw.get("source_record_id") or raw_id)

        if not val_res.is_valid:
            # Mark as unusable quarantine
            cand_dict = dict(raw)
            cand_dict["sample_id"] = f"train_{raw_id}" if not raw_id.startswith("train_") else raw_id
            cand_dict["local_path"] = computed_local_path
            cand_dict["sha256"] = val_res.sha256 or "0" * 64
            cand_dict["dhash"] = val_res.phash or "0" * 16
            cand_dict["width"] = max(val_res.width, 1)
            cand_dict["height"] = max(val_res.height, 1)
            cand_dict["file_size_bytes"] = max(val_res.file_size_bytes, 1)
            cand_dict["mime_type"] = val_res.mime_type or "image/jpeg"
            cand_dict["primary_category"] = normalize_category_label(raw.get("canonical_category") or raw.get("category"))
            cand_dict["ambiguity_status"] = AmbiguityStatus.UNUSABLE.value
            cand_dict["verification_status"] = "QUARANTINED"
            cand_dict["reviewer_notes"] = f"Image validation failed: {val_res.rejection_reason}"
            cand_dict["split"] = TrainingSplit.QUARANTINE.value
            cand_dict["quality_flags"] = quality_flags
            cand_dict["license"] = resolved_license
            cand_dict["license_url"] = resolved_license_url
            cand_dict["license_scope"] = LicenseScope.DATASET.value
            cand_dict["source_url"] = resolved_source_url
            cand_dict["source_record_id"] = resolved_rec_id
            validated_candidates.append(cand_dict)
            continue

        # Valid image record
        cand_dict = dict(raw)
        cand_dict["sample_id"] = f"train_{raw_id}" if not raw_id.startswith("train_") else raw_id
        cand_dict["local_path"] = computed_local_path
        cand_dict["sha256"] = val_res.sha256
        cand_dict["dhash"] = val_res.phash
        cand_dict["width"] = val_res.width
        cand_dict["height"] = val_res.height
        cand_dict["file_size_bytes"] = val_res.file_size_bytes
        cand_dict["mime_type"] = val_res.mime_type or "image/jpeg"
        cand_dict["primary_category"] = normalize_category_label(raw.get("canonical_category") or raw.get("category"))
        cand_dict["quality_flags"] = quality_flags
        cand_dict["license"] = resolved_license
        cand_dict["license_url"] = resolved_license_url
        cand_dict["license_scope"] = LicenseScope.DATASET.value
        cand_dict["source_url"] = resolved_source_url
        cand_dict["source_record_id"] = resolved_rec_id

        cand_dict["subtype"] = raw.get("subtype")
        if raw.get("reviewer_notes"):
            cand_dict["reviewer_notes"] = raw["reviewer_notes"]

        validated_candidates.append(cand_dict)

    # 4. Leakage audit against benchmark
    leakage_report = leakage_index.audit_candidates(validated_candidates)
    rejection_map = {r["sample_id"]: r for r in leakage_report.get("rejected_samples", [])}

    for cand in validated_candidates:
        sid = cand["sample_id"]
        if sid in rejection_map:
            rej = rejection_map[sid]
            cand["benchmark_leakage_check"] = {
                "status": str(rej["status"]).lower(),
                "checked": True,
                "passed": False,
                "min_dhash_distance": rej.get("min_dhash_distance"),
                "matched_benchmark_sample_id": rej.get("matched_benchmark_sample_id"),
                "details": rej.get("details"),
            }
            cand["ambiguity_status"] = AmbiguityStatus.QUARANTINE.value
            cand["verification_status"] = "QUARANTINED"
            cand["split"] = TrainingSplit.QUARANTINE.value
            cand["reviewer_notes"] = f"Quarantined due to benchmark leakage: {rej['rejection_reason']}"
        else:
            cand["benchmark_leakage_check"] = {
                "status": LeakageStatus.PASSED.value,
                "checked": True,
                "passed": True,
                "min_dhash_distance": None,
                "details": "Passed all benchmark leakage checks",
            }
            cand["ambiguity_status"] = cand.get("ambiguity_status") or AmbiguityStatus.CLEAR.value
            cand["verification_status"] = cand.get("verification_status") or "SOURCE_LABEL"
            cand["verification_method"] = cand.get("verification_method") or VerificationMethod.SOURCE_LABEL.value

    # 5. Intra-dataset duplicate analysis
    duplicate_report = detect_intra_dataset_duplicates(validated_candidates)

    # 6. Group assignment
    grouped_candidates = assign_group_ids(validated_candidates)

    # 7. Deterministic Train / Validation / Quarantine Split
    split_result = split_training_dataset(grouped_candidates, seed=seed, train_ratio=train_ratio)
    train_recs = split_result["train_records"]
    val_recs = split_result["validation_records"]
    quar_recs = split_result["quarantine_records"]

    all_processed: list[TrainingSample] = []
    for r in train_recs + val_recs + quar_recs:
        sample_obj = TrainingSample.model_validate(r)
        all_processed.append(sample_obj)

    # 8. Write manifests and split JSONL files
    manifest_jsonl_path = output_dir / "manifest.jsonl"
    with open(manifest_jsonl_path, "w", encoding="utf-8") as f:
        for s in all_processed:
            f.write(s.model_dump_json() + "\n")

    train_jsonl_path = splits_dir / "train.jsonl"
    with open(train_jsonl_path, "w", encoding="utf-8") as f:
        for r in train_recs:
            s = TrainingSample.model_validate(r)
            f.write(s.model_dump_json() + "\n")

    val_jsonl_path = splits_dir / "validation.jsonl"
    with open(val_jsonl_path, "w", encoding="utf-8") as f:
        for r in val_recs:
            s = TrainingSample.model_validate(r)
            f.write(s.model_dump_json() + "\n")

    quar_jsonl_path = splits_dir / "quarantine.jsonl"
    with open(quar_jsonl_path, "w", encoding="utf-8") as f:
        for r in quar_recs:
            s = TrainingSample.model_validate(r)
            f.write(s.model_dump_json() + "\n")

    # 9. Compute class and source distributions
    class_dist: dict[str, dict[str, int]] = {}
    for cat in CANONICAL_CATEGORIES:
        class_dist[cat] = {"train": 0, "validation": 0, "quarantine": 0, "total": 0}

    for s in all_processed:
        c = s.primary_category
        sp = s.split.value
        class_dist[c][sp] += 1
        class_dist[c]["total"] += 1

    source_dist: dict[str, int] = {}
    for s in all_processed:
        source_dist[s.source_name] = source_dist.get(s.source_name, 0) + 1

    # 10. Write dataset summary
    group_ids = {s.group_id for s in all_processed}
    multi_issue_count = sum(1 for s in all_processed if s.has_multiple_issues)
    quality_summary: dict[str, int] = {}
    for s in all_processed:
        for q in s.quality_flags:
            quality_summary[q] = quality_summary.get(q, 0) + 1

    summary_obj = TrainingDatasetSummary(
        dataset_version="training_v1",
        total_samples=len(all_processed),
        train_samples=len(train_recs),
        validation_samples=len(val_recs),
        quarantine_samples=len(quar_recs),
        class_distribution=class_dist,
        source_distribution=source_dist,
        group_count=len(group_ids),
        multi_issue_count=multi_issue_count,
        quality_flags_summary=quality_summary,
        leakage_check_summary=leakage_report.get("rejection_breakdown", {}),
        created_at=datetime.now(UTC).isoformat(),
        schema_version="1.0.0",
    )

    summary_path = output_dir / "dataset_summary.json"
    summary_path.write_text(summary_obj.model_dump_json(indent=2), encoding="utf-8")

    # 11. Write reports
    (reports_dir / "leakage_report.json").write_text(json.dumps(leakage_report, indent=2), encoding="utf-8")
    (reports_dir / "duplicate_report.json").write_text(json.dumps(duplicate_report, indent=2), encoding="utf-8")
    (reports_dir / "quality_report.json").write_text(json.dumps({
        "total_evaluated": len(quality_report_items),
        "valid_count": sum(1 for q in quality_report_items if q["is_valid"]),
        "invalid_count": sum(1 for q in quality_report_items if not q["is_valid"]),
        "quality_warnings_summary": quality_summary,
        "items": quality_report_items,
    }, indent=2), encoding="utf-8")
    (reports_dir / "class_distribution.json").write_text(json.dumps(class_dist, indent=2), encoding="utf-8")
    (reports_dir / "source_distribution.json").write_text(json.dumps(source_dist, indent=2), encoding="utf-8")

    # 12. Write curation report
    curation_report = {
        "pipeline_version": "1.0.0",
        "curation_timestamp": datetime.now(UTC).isoformat(),
        "input_raw_candidates": len(candidate_raw_list),
        "total_manifest_samples": len(all_processed),
        "clean_train_samples": len(train_recs),
        "clean_validation_samples": len(val_recs),
        "quarantined_samples": len(quar_recs),
        "leakage_rejections": len(rejection_map),
        "intra_duplicate_matches": duplicate_report["near_duplicates_count"],
        "class_distribution": class_dist,
        "source_distribution": source_dist,
        "split_ratio_target": f"{int(train_ratio*100)}/{int((1-train_ratio)*100)}",
        "benchmark_integrity_verified": leakage_index.is_manifest_verified,
    }
    (reports_dir / "curation_report.json").write_text(json.dumps(curation_report, indent=2), encoding="utf-8")

    # 13. Write source registry provenance
    registry_export = {k: asdict(v) for k, v in DATASET_REGISTRY.items()}
    (prov_dir / "source_registry.json").write_text(json.dumps(registry_export, indent=2), encoding="utf-8")

    # 14. Write README.md
    readme_content = f"""# CivicSense Training Dataset (training_v1)

**Version:** 1.0.0
**Generated:** {curation_report['curation_timestamp']}
**Status:** Curated Foundation Pool (Zero Benchmark Leakage)

## Overview
- **Total Registered Samples:** {len(all_processed)}
- **Clean Training Set (`splits/train.jsonl`):** {len(train_recs)}
- **Clean Validation Set (`splits/validation.jsonl`):** {len(val_recs)}
- **Quarantined Samples (`splits/quarantine.jsonl`):** {len(quar_recs)}
- **Benchmark Leakage Rejections:** {len(rejection_map)} (100% quarantined)

## Directory Structure
```
datasets/training_v1/
├── README.md                     # Dataset documentation
├── manifest.jsonl                # Master manifest containing all records
├── dataset_summary.json          # Dataset metadata and aggregated distributions
├── splits/
│   ├── train.jsonl               # Clean training split (group isolated)
│   ├── validation.jsonl          # Clean validation split (group isolated)
│   └── quarantine.jsonl          # Quarantined / ambiguous / leaked samples
├── reports/
│   ├── curation_report.json      # Pipeline execution summary
│   ├── leakage_report.json       # Benchmark leakage verification details
│   ├── duplicate_report.json     # Intra-dataset duplicates and near-duplicates
│   ├── quality_report.json       # Image decodability, dimensions, quality flags
│   ├── class_distribution.json   # Category breakdown per split
│   └── source_distribution.json  # Source breakdown per split
└── provenance/
    └── source_registry.json      # License, redistribution, and legal provenance
```

## Governance Invariants
1. **Benchmark Isolation**: No sample in `train.jsonl` or `validation.jsonl` collides with `datasets/benchmark_v1/` by SHA-256, Source ID, URL, or 64-bit dHash (\\le 6 bits).
2. **Group-Level Isolation**: No `group_id` spans across both train and validation splits.
3. **Quarantine Policy**: Ambiguous and leakage-detected records are quarantined and excluded from training.
"""
    (output_dir / "README.md").write_text(readme_content, encoding="utf-8")

    return curation_report


def main() -> None:
    parser = argparse.ArgumentParser(description="CivicSense Training Dataset Curation Runner")
    parser.add_argument("--raw-dir", type=Path, default=repo_root / "datasets" / "raw")
    parser.add_argument("--benchmark-dir", type=Path, default=repo_root / "datasets" / "benchmark_v1")
    parser.add_argument("--output-dir", type=Path, default=repo_root / "datasets" / "training_v1")
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    report = curate_training_pipeline(
        raw_dir=args.raw_dir,
        benchmark_dir=args.benchmark_dir,
        output_dir=args.output_dir,
        train_ratio=args.train_ratio,
        seed=args.seed,
    )
    print("Curation completed successfully:")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
