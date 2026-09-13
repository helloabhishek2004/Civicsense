"""CivicSense Dataset Source Diversity & Quality Audit Reporter.

Analyzes training dataset composition across:
- Sources (total, clean, quarantined, train, validation)
- Classes per source
- Acquisition batches (initial_pool, batch_1, batch_2, batch_3)
- Classes per acquisition batch
- License compliance and distribution
- Geographic and locality distribution
- Incident / group ID distribution and group sizes
- Source and class concentration indices (HHI, entropy, imbalance ratios)
- Subtype distribution for 'Other'
- Acceptance and quarantine rates by source

Outputs: datasets/training_v1/reports/source_diversity_report.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

repo_root = Path(__file__).resolve().parents[2]
backend_path = repo_root / "backend"
for _p in (str(repo_root), str(backend_path)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CANONICAL_CATEGORIES = [
    "Pothole",
    "Road Damage",
    "Garbage",
    "Water Leakage",
    "Streetlight",
    "Other",
]


def load_acquisition_batch_map(acquisition_dir: Path) -> dict[str, str]:
    """Map sample_id to acquisition batch string based on manifest files."""
    sample_to_batch: dict[str, str] = {}
    if not acquisition_dir.exists():
        return sample_to_batch

    for mf in sorted(acquisition_dir.glob("*_manifest.json")):
        batch_name = mf.stem.replace("_manifest", "")
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            for cand in data.get("candidates", []):
                sid = cand.get("sample_id")
                if sid:
                    sample_to_batch[sid] = batch_name
                    # Also map prefix variations if any
                    if not sid.startswith("train_"):
                        sample_to_batch[f"train_{sid}"] = batch_name
        except Exception:  # noqa: BLE001, S110
            pass
    return sample_to_batch


def load_raw_geographic_metadata(raw_dir: Path) -> dict[str, dict[str, Any]]:
    """Map source_record_id and sample_id to geographic metadata."""
    geo_map: dict[str, dict[str, Any]] = {}
    if not raw_dir.exists():
        return geo_map

    for src_dir in raw_dir.iterdir():
        if not src_dir.is_dir():
            continue
        rs_file = src_dir / "raw_samples.json"
        if rs_file.exists():
            try:
                data = json.loads(rs_file.read_text(encoding="utf-8"))
                for item in data:
                    sid = item.get("sample_id")
                    srid = item.get("source_record_id")
                    meta = item.get("original_metadata") or {}
                    loc = meta.get("location") or item.get("location") or "Unknown"
                    neigh = meta.get("neighborhood") or meta.get("district") or "Unknown"
                    lat = meta.get("latitude")
                    lon = meta.get("longitude")
                    info = {
                        "location": loc,
                        "neighborhood": neigh,
                        "has_coordinates": bool(lat and lon),
                    }
                    if sid:
                        geo_map[sid] = info
                        geo_map[f"train_{sid}"] = info
                    if srid:
                        geo_map[str(srid)] = info
            except Exception:  # noqa: BLE001, S110
                pass
    return geo_map


def compute_source_diversity_report(
    training_dir: Path | str,
    raw_dir: Path | str,
    output_report_path: Path | str | None = None,
) -> dict[str, Any]:
    """Compile comprehensive source diversity and quality audit report."""
    t_dir = Path(training_dir)
    r_dir = Path(raw_dir)
    acq_dir = t_dir / "acquisition"

    manifest_file = t_dir / "manifest.jsonl"
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_file}")

    manifest_records: list[dict[str, Any]] = []
    with open(manifest_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                manifest_records.append(json.loads(line))

    batch_map = load_acquisition_batch_map(acq_dir)
    geo_map = load_raw_geographic_metadata(r_dir)

    # 1. Split distribution
    train_records = [r for r in manifest_records if r.get("split") == "train"]
    val_records = [r for r in manifest_records if r.get("split") == "validation"]
    quar_records = [r for r in manifest_records if r.get("split") == "quarantine"]
    clean_records = train_records + val_records

    total_samples = len(manifest_records)
    clean_total = len(clean_records)
    quar_total = len(quar_records)

    # 2. Source distribution
    samples_per_source: dict[str, dict[str, int]] = {}
    for r in manifest_records:
        src = r.get("source_name", "unknown")
        split = r.get("split", "unknown")
        if src not in samples_per_source:
            samples_per_source[src] = {
                "total": 0,
                "clean": 0,
                "train": 0,
                "validation": 0,
                "quarantine": 0,
            }
        samples_per_source[src]["total"] += 1
        if split in ("train", "validation"):
            samples_per_source[src]["clean"] += 1
            samples_per_source[src][split] += 1
        elif split == "quarantine":
            samples_per_source[src]["quarantine"] += 1

    # 3. Samples per class per source (clean pool)
    clean_by_class_source: dict[str, dict[str, int]] = {}
    for r in clean_records:
        cat = r.get("primary_category", "Other")
        src = r.get("source_name", "unknown")
        clean_by_class_source.setdefault(cat, Counter())[src] += 1
    clean_by_class_source_dict = {
        cat: dict(cnt) for cat, cnt in clean_by_class_source.items()
    }

    # 4. Acquisition batch analysis
    samples_per_batch: dict[str, dict[str, int]] = {}
    clean_by_class_batch: dict[str, dict[str, int]] = {}

    for r in manifest_records:
        sid = r.get("sample_id", "")
        batch = batch_map.get(sid, "initial_pool")
        split = r.get("split", "unknown")
        cat = r.get("primary_category", "Other")

        if batch not in samples_per_batch:
            samples_per_batch[batch] = {
                "total": 0,
                "clean": 0,
                "train": 0,
                "validation": 0,
                "quarantine": 0,
            }
        samples_per_batch[batch]["total"] += 1
        if split in ("train", "validation"):
            samples_per_batch[batch]["clean"] += 1
            samples_per_batch[batch][split] += 1
            clean_by_class_batch.setdefault(cat, Counter())[batch] += 1
        else:
            samples_per_batch[batch]["quarantine"] += 1

    clean_by_class_batch_dict = {
        cat: dict(cnt) for cat, cnt in clean_by_class_batch.items()
    }

    # 5. License distribution
    licenses_total: Counter[str] = Counter()
    licenses_clean: Counter[str] = Counter()
    for r in manifest_records:
        lic = r.get("license") or "Unknown"
        licenses_total[lic] += 1
        if r.get("split") in ("train", "validation"):
            licenses_clean[lic] += 1

    # 6. Geographic distribution
    geo_counts_clean: Counter[str] = Counter()
    coords_available_clean = 0
    for r in clean_records:
        sid = r.get("sample_id", "")
        src = r.get("source_name", "")
        info = geo_map.get(sid) or geo_map.get(str(r.get("source_record_id", ""))) or {}
        if info.get("has_coordinates"):
            coords_available_clean += 1
        if "boston" in src:
            neigh = info.get("neighborhood")
            geo_counts_clean[f"Boston, MA ({neigh})" if neigh and neigh != "Unknown" else "Boston, MA"] += 1
        elif "wikimedia" in src:
            geo_counts_clean["Global / Wikimedia Commons"] += 1
        elif "taco" in src:
            geo_counts_clean["Global / TACO Open Web"] += 1
        else:
            geo_counts_clean["Unspecified Open Web"] += 1

    # 7. Incident / group ID analysis
    groups_clean: set[str] = set()
    train_groups: set[str] = set()
    val_groups: set[str] = set()
    group_sizes_clean: Counter[str] = Counter()

    for r in clean_records:
        gid = r.get("group_id", "ungrouped")
        groups_clean.add(gid)
        group_sizes_clean[gid] += 1
        if r.get("split") == "train":
            train_groups.add(gid)
        elif r.get("split") == "validation":
            val_groups.add(gid)

    overlap_groups = train_groups.intersection(val_groups)
    sizes = list(group_sizes_clean.values())
    group_stats = {
        "total_unique_clean_groups": len(groups_clean),
        "train_unique_groups": len(train_groups),
        "validation_unique_groups": len(val_groups),
        "overlapping_groups_between_splits": len(overlap_groups),
        "group_isolation_verified": len(overlap_groups) == 0,
        "mean_images_per_group": round(sum(sizes) / len(sizes), 2) if sizes else 0.0,
        "max_images_in_single_group": max(sizes) if sizes else 0,
        "min_images_in_group": min(sizes) if sizes else 0,
        "single_image_groups_count": sum(1 for s in sizes if s == 1),
        "multi_image_groups_count": sum(1 for s in sizes if s > 1),
    }

    # 8. Concentration metrics
    # Herfindahl-Hirschman Index (HHI) for sources (clean pool)
    # Range: 1/N (perfectly balanced) to 1.0 (monopoly)
    source_shares = [
        (counts["clean"] / clean_total)
        for counts in samples_per_source.values()
        if counts["clean"] > 0
    ] if clean_total > 0 else []
    hhi_source = round(sum(s**2 for s in source_shares), 4)

    # Class balance ratio (min class count / max class count in clean pool)
    class_clean_counts = Counter(r.get("primary_category", "Other") for r in clean_records)
    min_class_count = min(class_clean_counts.values()) if class_clean_counts else 0
    max_class_count = max(class_clean_counts.values()) if class_clean_counts else 0
    class_balance_ratio = round(min_class_count / max_class_count, 3) if max_class_count > 0 else 0.0

    # Shannon entropy for clean classes
    entropy_class = 0.0
    if clean_total > 0:
        for cnt in class_clean_counts.values():
            p = cnt / clean_total
            if p > 0:
                entropy_class -= p * math.log2(p)
    entropy_class = round(entropy_class, 3)
    max_entropy = round(math.log2(len(CANONICAL_CATEGORIES)), 3)

    # 9. Other subtype distribution
    other_subtypes_clean: Counter[str] = Counter()
    other_subtypes_quar: Counter[str] = Counter()
    for r in manifest_records:
        if r.get("primary_category") == "Other":
            st = r.get("subtype") or "unspecified"
            if r.get("split") in ("train", "validation"):
                other_subtypes_clean[st] += 1
            else:
                other_subtypes_quar[st] += 1

    # 10. Acceptance and quarantine rates by source
    source_acceptance_rates: dict[str, dict[str, Any]] = {}
    for src, counts in samples_per_source.items():
        tot = counts["total"]
        cln = counts["clean"]
        quar = counts["quarantine"]
        rate = round(cln / tot * 100, 1) if tot > 0 else 0.0
        source_acceptance_rates[src] = {
            "total_evaluated": tot,
            "accepted_clean": cln,
            "quarantined": quar,
            "acceptance_rate_pct": rate,
            "quarantine_rate_pct": round(100.0 - rate, 1) if tot > 0 else 0.0,
        }

    report: dict[str, Any] = {
        "report_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_manifest_records": total_samples,
            "clean_total": clean_total,
            "clean_train": len(train_records),
            "clean_validation": len(val_records),
            "quarantined_total": quar_total,
            "clean_pool_acceptance_rate": (
                f"{round(clean_total / total_samples * 100, 1)}%" if total_samples > 0 else "0%"
            ),
        },
        "source_distribution": samples_per_source,
        "clean_samples_by_class_and_source": clean_by_class_source_dict,
        "acquisition_batch_distribution": samples_per_batch,
        "clean_samples_by_class_and_batch": clean_by_class_batch_dict,
        "license_distribution": {
            "clean_pool": dict(licenses_clean),
            "total_manifest": dict(licenses_total),
        },
        "geographic_distribution_clean_pool": {
            "locations_identified": dict(geo_counts_clean.most_common(20)),
            "samples_with_coordinates": coords_available_clean,
            "coordinate_coverage_pct": (
                round(coords_available_clean / clean_total * 100, 1) if clean_total > 0 else 0.0
            ),
        },
        "incident_group_analysis": group_stats,
        "concentration_and_balance_metrics": {
            "source_herfindahl_index": hhi_source,
            "source_diversity_interpretation": (
                "Highly diverse" if hhi_source < 0.25 else
                "Moderately concentrated" if hhi_source < 0.50 else
                "Highly concentrated"
            ),
            "class_balance_ratio_min_to_max": class_balance_ratio,
            "class_entropy": entropy_class,
            "max_possible_entropy": max_entropy,
            "entropy_ratio": round(entropy_class / max_entropy, 3) if max_entropy > 0 else 0.0,
            "min_class_count": min_class_count,
            "max_class_count": max_class_count,
        },
        "other_subtype_breakdown": {
            "clean_pool": dict(other_subtypes_clean),
            "quarantine_pool": dict(other_subtypes_quar),
        },
        "source_acceptance_and_quarantine_rates": source_acceptance_rates,
    }

    if output_report_path:
        out_p = Path(output_report_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CivicSense Dataset Source Diversity & Quality Audit Reporter"
    )
    parser.add_argument(
        "--training-dir",
        type=Path,
        default=repo_root / "datasets" / "training_v1",
        help="Path to training_v1 directory",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=repo_root / "datasets" / "raw",
        help="Path to raw datasets directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "datasets" / "training_v1" / "reports" / "source_diversity_report.json",
        help="Path for output JSON report",
    )
    args = parser.parse_args()

    report = compute_source_diversity_report(
        training_dir=args.training_dir,
        raw_dir=args.raw_dir,
        output_report_path=args.output,
    )

    print("=" * 65)
    print("CIVICSENSE SOURCE DIVERSITY & QUALITY AUDIT")
    print("=" * 65)
    print(f"Total Manifest Records : {report['summary']['total_manifest_records']}")
    print(f"Clean Pool (Train/Val) : {report['summary']['clean_total']} ({report['summary']['clean_train']} / {report['summary']['clean_validation']})")
    print(f"Quarantined Records    : {report['summary']['quarantined_total']}")
    print("-" * 65)
    print("Clean Pool by Source:")
    for src, cnts in sorted(report["source_distribution"].items(), key=lambda x: -x[1]["clean"]):
        print(f"  {src:30s}: clean={cnts['clean']:4d} (train={cnts['train']:3d}, val={cnts['validation']:3d}) | total={cnts['total']:4d}")
    print("-" * 65)
    print("Clean Pool by Batch:")
    for bch, cnts in sorted(report["acquisition_batch_distribution"].items(), key=lambda x: -x[1]["clean"]):
        print(f"  {bch:20s}: clean={cnts['clean']:4d} | total={cnts['total']:4d}")
    print("-" * 65)
    print("Concentration & Balance:")
    print(f"  Source HHI Index      : {report['concentration_and_balance_metrics']['source_herfindahl_index']} ({report['concentration_and_balance_metrics']['source_diversity_interpretation']})")
    print(f"  Class Balance Ratio   : {report['concentration_and_balance_metrics']['class_balance_ratio_min_to_max']} (min={report['concentration_and_balance_metrics']['min_class_count']}, max={report['concentration_and_balance_metrics']['max_class_count']})")
    print(f"  Class Shannon Entropy : {report['concentration_and_balance_metrics']['class_entropy']} / {report['concentration_and_balance_metrics']['max_possible_entropy']} ({report['concentration_and_balance_metrics']['entropy_ratio']*100:.1f}%)")
    print("-" * 65)
    print("Incident Group Isolation:")
    print(f"  Unique Groups in Clean: {report['incident_group_analysis']['total_unique_clean_groups']}")
    print(f"  Overlapping Groups    : {report['incident_group_analysis']['overlapping_groups_between_splits']} (Isolation Verified: {report['incident_group_analysis']['group_isolation_verified']})")
    print(f"  Mean Images / Group   : {report['incident_group_analysis']['mean_images_per_group']}")
    print("=" * 65)
    print(f"Saved JSON report to: {args.output}")


if __name__ == "__main__":
    main()
