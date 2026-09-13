"""CivicSense Benchmark Curation Engine.

Coordinates annotation normalization, image validation, deduplication, and
category balancing to generate the canonical benchmark dataset:
- datasets/benchmark_v1/benchmark_dataset.jsonl
- datasets/benchmark_v1/manifest.json
- datasets/benchmark_v1/curation_report.json

Enforces:
- Target: 300 samples (50 per category).
- Strictly NO synthetic duplication or relabeling if categories are below 50.
- Validates every record through EvaluationSample.
"""

import argparse
import datetime
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Ensure repo root and backend package are in sys.path when run as standalone script
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.evaluation.schema import (  # noqa: E402
    BenchmarkManifest,
    BenchmarkSplit,
    EvaluationSample,
)
from scripts.datasets.deduplicate_benchmark import run_deduplication  # noqa: E402
from scripts.datasets.normalize_annotations import (  # noqa: E402
    MappingOutcome,
    normalize_annotation,
)
from scripts.datasets.validate_images import validate_image_file  # noqa: E402

TARGET_PER_CATEGORY = 50
CANONICAL_CATEGORIES = [
    "Pothole",
    "Road Damage",
    "Garbage",
    "Water Leakage",
    "Streetlight",
    "Other",
]


def curate_benchmark(
    candidate_records: list[dict[str, Any]],
    images_root: Path,
    output_dir: Path,
    target_per_category: int = TARGET_PER_CATEGORY,
    dedup_threshold: int = 4,
    benchmark_version: str = "1.0.0",
    copy_images: bool = False,
) -> dict[str, Any]:
    """Assemble verified benchmark files from candidate records."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_root = Path(images_root).resolve()

    curation_log: list[str] = []
    rejected_records: list[dict[str, Any]] = []
    valid_candidates: list[dict[str, Any]] = []

    # 1. Normalization & Image Validation
    for raw_rec in candidate_records:
        sample_id = str(raw_rec.get("sample_id") or f"sample_{len(valid_candidates) + 1:06d}")
        source_dataset = str(raw_rec.get("source_dataset", "unknown"))
        raw_label = str(raw_rec.get("original_category", ""))
        rel_img_path = raw_rec.get("image_rel_path")

        # Normalize annotation
        norm = normalize_annotation(
            source_dataset=source_dataset,
            source_record_id=str(raw_rec.get("source_record_id", sample_id)),
            original_category=raw_label,
            original_annotation=raw_rec.get("original_annotation", {}),
            text_description=raw_rec.get("text_description"),
            bounding_boxes=raw_rec.get("bounding_boxes", []),
            source_license=raw_rec.get("license", "unverified"),
            license_url=raw_rec.get("license_url", ""),
            attribution=raw_rec.get("attribution", ""),
            source_url=raw_rec.get("source_url"),
        )

        if norm.outcome != MappingOutcome.ACCEPTED or not norm.canonical_category:
            rejected_records.append({
                "sample_id": sample_id,
                "reason": f"Normalization rejected: {norm.mapping_rationale}",
                "raw_record": raw_rec,
            })
            continue

        # Image validation
        if not rel_img_path:
            rejected_records.append({
                "sample_id": sample_id,
                "reason": "Missing image_rel_path",
                "raw_record": raw_rec,
            })
            continue

        full_img_path = images_root / rel_img_path
        val_result = validate_image_file(full_img_path, base_dir=images_root)
        if not val_result.is_valid:
            rejected_records.append({
                "sample_id": sample_id,
                "reason": f"Image validation failed: {val_result.rejection_reason}",
                "path": str(full_img_path),
            })
            continue

        valid_candidates.append({
            "sample_id": sample_id,
            "image_rel_path": str(rel_img_path).replace("\\", "/"),
            "source_dataset": norm.source_dataset,
            "source_record_id": norm.source_record_id,
            "canonical_category": norm.canonical_category,
            "original_category": norm.original_category,
            "category_confidence": 1.0,
            "bounding_boxes": norm.bounding_boxes,
            "text_description": norm.text_description,
            "split": BenchmarkSplit.BENCHMARK.value,
            "license": norm.source_license,
            "license_url": norm.license_url,
            "attribution": norm.attribution,
            "is_blurry": val_result.is_blurry,
            "is_low_res": val_result.is_low_res,
            "sha256": val_result.sha256,
            "phash": val_result.phash,
            "duplicate_group_id": None,
            "review_status": "CONFIRMED",
            "verification_level": norm.verification_level,
            "visual_relevance": norm.visual_relevance,
            "metadata_json": raw_rec.get("metadata_json", {}),
        })

    # 2. Deduplication
    retained_after_dedup, dedup_report = run_deduplication(
        valid_candidates, phash_threshold=dedup_threshold
    )

    # 3. Category Stratification & Balancing
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in retained_after_dedup:
        cat = sample["canonical_category"]
        by_category[cat].append(sample)

    selected_samples: list[EvaluationSample] = []
    category_counts: dict[str, int] = {}
    shortages: dict[str, int] = {}

    for cat in CANONICAL_CATEGORIES:
        available = by_category.get(cat, [])
        available.sort(key=lambda s: (s["canonical_category"], s["sample_id"]))
        count = len(available)

        if count < target_per_category:
            shortage = target_per_category - count
            shortages[cat] = shortage
            curation_log.append(
                f"SHORTAGE WARNING: Category '{cat}' has {count} valid samples "
                f"(shortage: {shortage} vs target {target_per_category}). "
                "Retaining actual count without synthetic duplication."
            )
            selected_for_cat = available
        else:
            selected_for_cat = available[:target_per_category]

        category_counts[cat] = len(selected_for_cat)
        for sample_dict in selected_for_cat:
            if copy_images:
                dest_dir = output_dir / "images"
                dest_dir.mkdir(parents=True, exist_ok=True)
                src_path = images_root / sample_dict["image_rel_path"]
                ext = src_path.suffix or ".jpg"
                dest_filename = f"{sample_dict['sample_id']}{ext}"
                dest_path = dest_dir / dest_filename
                shutil.copy2(src_path, dest_path)
                sample_dict = dict(sample_dict)
                sample_dict["image_rel_path"] = f"images/{dest_filename}"

            eval_sample = EvaluationSample.model_validate(sample_dict)
            selected_samples.append(eval_sample)

    selected_samples.sort(key=lambda item: (item.canonical_category, item.sample_id))

    # 4. Write benchmark_dataset.jsonl
    jsonl_path = output_dir / "benchmark_dataset.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for sample_obj in selected_samples:
            f.write(sample_obj.model_dump_json() + "\n")

    # 5. Source, verification, and relevance counts
    source_counts: dict[str, int] = defaultdict(int)
    verif_counts: dict[str, int] = defaultdict(int)
    vis_counts: dict[str, int] = defaultdict(int)
    for sample_obj in selected_samples:
        source_counts[sample_obj.source_dataset] += 1
        verif_counts[sample_obj.verification_level] += 1
        vis_counts[sample_obj.visual_relevance] += 1

    # 6. Generate manifest.json with SHA-256 integrity hash
    dataset_bytes = jsonl_path.read_bytes()
    manifest_integrity_hash = hashlib.sha256(dataset_bytes).hexdigest()

    manifest = BenchmarkManifest(
        benchmark_version=benchmark_version,
        generation_timestamp=datetime.datetime.now(datetime.UTC),
        total_sample_count=len(selected_samples),
        category_counts=category_counts,
        source_dataset_counts=dict(source_counts),
        verification_level_counts=dict(verif_counts),
        visual_relevance_counts=dict(vis_counts),
        image_root="images",
        integrity_hash=manifest_integrity_hash,
    )
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    # 7. Write curation_report.json
    report_data = {
        "benchmark_version": benchmark_version,
        "generation_timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "target_per_category": target_per_category,
        "total_selected": len(selected_samples),
        "category_counts": category_counts,
        "category_shortages": shortages,
        "source_counts": dict(source_counts),
        "verification_level_counts": dict(verif_counts),
        "visual_relevance_counts": dict(vis_counts),
        "total_candidates": len(candidate_records),
        "valid_candidates": len(valid_candidates),
        "rejected_count": len(rejected_records),
        "deduplication": dedup_report.to_dict(),
        "shortage_warnings": curation_log,
        "rejected_records_summary": rejected_records[:50],
    }
    curation_report_path = output_dir / "curation_report.json"
    with open(curation_report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    return report_data


def main() -> None:
    parser = argparse.ArgumentParser(description="CivicSense Benchmark Curation Tool")
    parser.add_argument("candidates_file", help="Path to JSON or JSONL candidate file")
    parser.add_argument("--images-root", required=True, help="Root directory for images")
    parser.add_argument("--output-dir", default="datasets/benchmark_v1", help="Output directory")
    parser.add_argument(
        "--target-per-category",
        type=int,
        default=TARGET_PER_CATEGORY,
        help="Target count per category",
    )
    parser.add_argument(
        "--dedup-threshold",
        type=int,
        default=4,
        help="pHash Hamming distance threshold",
    )
    parser.add_argument(
        "--copy-images",
        action="store_true",
        help="Copy selected images into output_dir/images/",
    )

    args = parser.parse_args()
    c_path = Path(args.candidates_file)
    if not c_path.exists():
        print(f"Error: Candidate file not found at {c_path}", file=sys.stderr)
        sys.exit(1)

    records: list[dict[str, Any]] = []
    if c_path.is_dir():
        raw_files = sorted(c_path.glob("**/raw_samples.json"))
        for rf in raw_files:
            with open(rf, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    records.extend(data)
    elif c_path.suffix.lower() == ".jsonl":
        with open(c_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    else:
        with open(c_path, encoding="utf-8") as f:
            records = json.load(f)

    report = curate_benchmark(
        candidate_records=records,
        images_root=Path(args.images_root),
        output_dir=Path(args.output_dir),
        target_per_category=args.target_per_category,
        dedup_threshold=args.dedup_threshold,
        copy_images=args.copy_images,
    )
    print(f"Benchmark curation complete. Total selected: {report['total_selected']}")


if __name__ == "__main__":
    main()
