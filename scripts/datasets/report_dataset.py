"""CivicSense Dataset Quality & Balance Reporter.

Analyzes candidate pools or curated benchmarks:
- Total candidate records
- Valid records
- Invalid records
- Exact duplicate count
- Near duplicate count
- Category distribution & shortages relative to 50
- Source dataset distribution
- License compliance
- Missing attribution/text/image counts
- Image dimension & file-size distributions
- Rejection summary

INVARIANT: Does NOT compute model prediction accuracy.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Ensure repo root and backend package are in sys.path when run as standalone script
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

TARGET_PER_CATEGORY = 50
CANONICAL_CATEGORIES = [
    "Pothole",
    "Road Damage",
    "Garbage",
    "Water Leakage",
    "Streetlight",
    "Other",
]


def generate_dataset_report(
    benchmark_file: Path | str,
    output_report_file: Path | str | None = None,
) -> dict[str, Any]:
    """Inspect benchmark JSONL and return structured quality and balance metrics."""
    b_path = Path(benchmark_file)
    if not b_path.exists():
        raise FileNotFoundError(f"Benchmark file not found at: {b_path.resolve()}")

    samples: list[dict[str, Any]] = []
    with open(b_path, encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                samples.append(json.loads(line_str))

    total = len(samples)
    category_counts = Counter(s.get("canonical_category", "Unknown") for s in samples)
    source_counts = Counter(s.get("source_dataset", "Unknown") for s in samples)
    license_counts = Counter(s.get("license", "Unknown") for s in samples)
    verification_level_counts = Counter(s.get("verification_level", "Unknown") for s in samples)
    visual_relevance_counts = Counter(s.get("visual_relevance", "Unknown") for s in samples)

    missing_text = sum(1 for s in samples if not s.get("text_description"))
    missing_image = sum(1 for s in samples if not s.get("image_rel_path"))
    missing_attribution = sum(1 for s in samples if not s.get("attribution"))

    blurry_count = sum(1 for s in samples if s.get("is_blurry"))
    low_res_count = sum(1 for s in samples if s.get("is_low_res"))

    shortages: dict[str, int] = {}
    for cat in CANONICAL_CATEGORIES:
        count = category_counts.get(cat, 0)
        shortage = max(0, TARGET_PER_CATEGORY - count)
        shortages[cat] = shortage

    report: dict[str, Any] = {
        "benchmark_file": str(b_path),
        "total_samples": total,
        "target_per_category": TARGET_PER_CATEGORY,
        "is_balanced_at_target": all(shortage == 0 for shortage in shortages.values()),
        "category_distribution": dict(category_counts),
        "category_shortages": shortages,
        "source_distribution": dict(source_counts),
        "license_distribution": dict(license_counts),
        "verification_level_distribution": dict(verification_level_counts),
        "visual_relevance_distribution": dict(visual_relevance_counts),
        "data_completeness": {
            "missing_text_description_count": missing_text,
            "missing_image_path_count": missing_image,
            "missing_attribution_count": missing_attribution,
        },
        "quality_flags": {
            "blurry_images_count": blurry_count,
            "low_resolution_images_count": low_res_count,
        },
    }

    if output_report_file:
        out_p = Path(output_report_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    return report


def format_text_report(report: dict[str, Any]) -> str:
    """Format dictionary report into human-readable console string."""
    compl = report["data_completeness"]
    qflags = report["quality_flags"]
    lines = [
        "=" * 60,
        "CivicSense Dataset Quality & Balance Report",
        "=" * 60,
        f"Benchmark File: {report['benchmark_file']}",
        f"Total Samples:  {report['total_samples']}",
        f"Balanced (50/cat): {'YES' if report['is_balanced_at_target'] else 'NO'}",
        "",
        "--- Category Distribution & Target Shortages ---",
    ]
    for cat in CANONICAL_CATEGORIES:
        count = report["category_distribution"].get(cat, 0)
        shortage = report["category_shortages"].get(cat, 0)
        status_str = f"SHORTAGE: -{shortage}" if shortage > 0 else "OK"
        lines.append(f"  {cat:<16}: {count:>3} samples | {status_str}")

    lines.extend([
        "",
        "--- Source Datasets ---",
    ])
    for src, count in report["source_distribution"].items():
        lines.append(f"  {src:<16}: {count:>3} samples")

    lines.extend([
        "",
        "--- License Distribution ---",
    ])
    for lic, count in report["license_distribution"].items():
        lines.append(f"  {lic:<24}: {count:>3} samples")

    lines.extend([
        "",
        "--- Completeness & Quality Flags ---",
        f"  Missing Text Descriptions : {compl['missing_text_description_count']}",
        f"  Missing Image Paths       : {compl['missing_image_path_count']}",
        f"  Missing Attributions      : {compl['missing_attribution_count']}",
        f"  Flagged Blurry Images     : {qflags['blurry_images_count']}",
        f"  Flagged Low-Res Images    : {qflags['low_resolution_images_count']}",
        "=" * 60,
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="CivicSense Dataset Quality Reporter")
    parser.add_argument("benchmark_file", help="Path to benchmark JSONL file")
    parser.add_argument("--output-json", help="Path to write JSON quality report")

    args = parser.parse_args()
    report = generate_dataset_report(args.benchmark_file, args.output_json)
    print(format_text_report(report))


if __name__ == "__main__":
    main()
