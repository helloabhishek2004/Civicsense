"""CivicSense Intra-Dataset Duplicate Detection & Deterministic Grouped Splitting.

Implements:
1. Intra-dataset duplicate and near-duplicate detection (exact SHA-256, source asset, dHash).
2. Evidence-based incident group assignment.
3. Deterministic group-level 80/20 train/validation splitting with zero group leakage,
   class stratification, and quarantine isolation.
"""

from __future__ import annotations

import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.evaluation.training_schema import AmbiguityStatus, TrainingSplit  # noqa: E402
from scripts.datasets.deduplicate_benchmark import hamming_distance  # noqa: E402

NEAR_DUPLICATE_DHASH_THRESHOLD = 4
BORDERLINE_DUPLICATE_DHASH_THRESHOLD = 6


@dataclass
class IntraDuplicateMatch:
    sample_id_1: str
    sample_id_2: str
    match_type: str  # "exact_duplicate", "same_source_asset", "near_duplicate", "borderline_match"
    dhash_distance: int | None = None
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_intra_dataset_duplicates(
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Identify exact and near-duplicates within the candidate training pool."""
    exact_matches: list[IntraDuplicateMatch] = []
    same_asset_matches: list[IntraDuplicateMatch] = []
    near_dup_matches: list[IntraDuplicateMatch] = []
    borderline_matches: list[IntraDuplicateMatch] = []

    # 1. Exact SHA-256 and Source ID indexing
    sha_map: dict[str, list[str]] = {}
    source_map: dict[tuple[str, str], list[str]] = {}

    for s in samples:
        sid = s["sample_id"]
        sha = s.get("sha256", "").lower().strip()
        if sha:
            sha_map.setdefault(sha, []).append(sid)

        src_name = s.get("source_name", s.get("source_dataset", "")).lower().strip()
        src_rec = str(s.get("source_record_id", "")).strip()
        if src_name and src_rec:
            source_map.setdefault((src_name, src_rec), []).append(sid)

    for sha, sids in sha_map.items():
        if len(sids) > 1:
            for i in range(len(sids)):
                for j in range(i + 1, len(sids)):
                    exact_matches.append(
                        IntraDuplicateMatch(
                            sample_id_1=sids[i],
                            sample_id_2=sids[j],
                            match_type="exact_duplicate",
                            dhash_distance=0,
                            details=f"Identical SHA-256: {sha}",
                        )
                    )

    for (src_name, src_rec), sids in source_map.items():
        if len(sids) > 1:
            for i in range(len(sids)):
                for j in range(i + 1, len(sids)):
                    same_asset_matches.append(
                        IntraDuplicateMatch(
                            sample_id_1=sids[i],
                            sample_id_2=sids[j],
                            match_type="same_source_asset",
                            details=f"Same source record ({src_name}, {src_rec})",
                        )
                    )

    # 2. Pairwise dHash comparison
    dhash_list = [
        (s["sample_id"], s.get("dhash", "").lower().strip())
        for s in samples
        if s.get("dhash") and len(s.get("dhash", "").strip()) == 16
    ]

    for i in range(len(dhash_list)):
        sid_1, dhash_1 = dhash_list[i]
        for j in range(i + 1, len(dhash_list)):
            sid_2, dhash_2 = dhash_list[j]
            dist = hamming_distance(dhash_1, dhash_2)
            if dist <= NEAR_DUPLICATE_DHASH_THRESHOLD:
                near_dup_matches.append(
                    IntraDuplicateMatch(
                        sample_id_1=sid_1,
                        sample_id_2=sid_2,
                        match_type="near_duplicate",
                        dhash_distance=dist,
                        details=f"dHash Hamming distance: {dist} bits",
                    )
                )
            elif dist <= BORDERLINE_DUPLICATE_DHASH_THRESHOLD:
                borderline_matches.append(
                    IntraDuplicateMatch(
                        sample_id_1=sid_1,
                        sample_id_2=sid_2,
                        match_type="borderline_match",
                        dhash_distance=dist,
                        details=f"Borderline dHash Hamming distance: {dist} bits",
                    )
                )

    return {
        "total_samples": len(samples),
        "exact_duplicates_count": len(exact_matches),
        "same_source_assets_count": len(same_asset_matches),
        "near_duplicates_count": len(near_dup_matches),
        "borderline_matches_count": len(borderline_matches),
        "exact_duplicates": [m.to_dict() for m in exact_matches],
        "same_source_assets": [m.to_dict() for m in same_asset_matches],
        "near_duplicates": [m.to_dict() for m in near_dup_matches],
        "borderline_matches": [m.to_dict() for m in borderline_matches],
    }


def assign_group_ids(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign stable, auditable group_id values using the strongest available evidence."""
    updated = []
    for s in samples:
        item = dict(s)
        existing_group = item.get("group_id")
        if existing_group and str(existing_group).strip():
            updated.append(item)
            continue

        src_name = str(item.get("source_name", item.get("source_dataset", ""))).lower().strip()
        src_rec = str(item.get("source_record_id", "")).strip()

        # Boston 311 incident grouping
        if "boston" in src_name and src_rec:
            # CRM service request ID represents a distinct municipal ticket/incident
            item["group_id"] = f"grp_bost_{src_rec}"
        elif "wikimedia" in src_name and src_rec:
            # Page ID or file name base
            item["group_id"] = f"grp_wm_{src_rec}"
        elif "taco" in src_name and src_rec:
            # TACO image ID or batch
            batch_id = item.get("metadata_json", {}).get("batch_id")
            if batch_id:
                item["group_id"] = f"grp_taco_batch_{batch_id}"
            else:
                item["group_id"] = f"grp_taco_{src_rec}"
        else:
            # Fallback to isolated sample group
            sample_id = item.get("sample_id", "unknown")
            item["group_id"] = f"grp_single_{sample_id}"

        updated.append(item)
    return updated


def split_training_dataset(
    samples: list[dict[str, Any]],
    seed: int = 42,
    train_ratio: float = 0.8,
) -> dict[str, Any]:
    """Deterministically partition candidate samples into train, validation, and quarantine.

    Invariants:
    1. Quarantine Isolation: Samples with ambiguity_status != 'clear', or explicit quarantine
       flags are assigned to QUARANTINE and NEVER enter train or validation.
    2. Group-Level Disjunction: No group_id can straddle both train and validation.
    3. Category Stratification: Preserves balanced class ratios across splits where feasible.
    """
    rng = random.Random(seed)

    quarantine_records: list[dict[str, Any]] = []
    clean_records: list[dict[str, Any]] = []

    non_clear_ambiguities = {
        AmbiguityStatus.AMBIGUOUS.value,
        AmbiguityStatus.QUARANTINE.value,
        AmbiguityStatus.UNUSABLE.value,
        AmbiguityStatus.OUT_OF_DOMAIN.value,
        AmbiguityStatus.NO_VISIBLE_ISSUE.value,
    }

    for s in samples:
        rec = dict(s)
        ambiguity = rec.get("ambiguity_status", AmbiguityStatus.CLEAR.value)
        verification = str(rec.get("verification_status", "")).upper()
        leakage_check = rec.get("benchmark_leakage_check", {})
        is_leakage_failed = leakage_check.get("checked", False) and not leakage_check.get("passed", True)

        if (
            ambiguity in non_clear_ambiguities
            or verification == "QUARANTINED"
            or is_leakage_failed
            or rec.get("split") == TrainingSplit.QUARANTINE.value
        ):
            rec["split"] = TrainingSplit.QUARANTINE.value
            quarantine_records.append(rec)
        else:
            clean_records.append(rec)

    # Group clean records by group_id
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in clean_records:
        gid = r["group_id"]
        groups.setdefault(gid, []).append(r)

    # Determine dominant primary category for each group
    group_categories: dict[str, str] = {}
    for gid, items in groups.items():
        cat_counts: dict[str, int] = {}
        for item in items:
            cat = item.get("primary_category", "Other")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        # Pick dominant category
        dominant_cat = max(cat_counts.items(), key=lambda kv: kv[1])[0]
        group_categories[gid] = dominant_cat

    # Partition groups by category to perform stratified group-level split
    category_groups: dict[str, list[str]] = {}
    for gid, cat in group_categories.items():
        category_groups.setdefault(cat, []).append(gid)

    train_group_ids: set[str] = set()
    val_group_ids: set[str] = set()

    for cat in sorted(category_groups.keys()):
        gids = sorted(category_groups[cat])  # Sort for determinism before shuffle
        rng.shuffle(gids)

        total_cat_samples = sum(len(groups[gid]) for gid in gids)
        target_train_count = int(round(total_cat_samples * train_ratio))

        current_train_count = 0
        for gid in gids:
            group_size = len(groups[gid])
            # If adding this group doesn't drastically exceed target, or if train is empty
            if (current_train_count + group_size <= target_train_count) or (current_train_count == 0):
                train_group_ids.add(gid)
                current_train_count += group_size
            else:
                val_group_ids.add(gid)

    train_records: list[dict[str, Any]] = []
    val_records: list[dict[str, Any]] = []

    for r in clean_records:
        gid = r["group_id"]
        if gid in train_group_ids:
            r["split"] = TrainingSplit.TRAIN.value
            train_records.append(r)
        elif gid in val_group_ids:
            r["split"] = TrainingSplit.VALIDATION.value
            val_records.append(r)
        else:
            # Fallback safe assignment
            r["split"] = TrainingSplit.TRAIN.value
            train_records.append(r)

    # Verification: Disjunction invariant
    overlap = train_group_ids.intersection(val_group_ids)
    if overlap:
        msg = f"Fatal split integrity error: group_ids appear in both train and validation: {overlap}"
        raise ValueError(msg)

    # Compute distribution statistics
    def _compute_stats(recs: list[dict[str, Any]]) -> dict[str, Any]:
        cats: dict[str, int] = {}
        sources: dict[str, int] = {}
        gids: set[str] = set()
        for r in recs:
            c = r.get("primary_category", "Other")
            cats[c] = cats.get(c, 0) + 1
            s = r.get("source_name", r.get("source_dataset", "unknown"))
            sources[s] = sources.get(s, 0) + 1
            gids.add(r.get("group_id", ""))
        return {
            "total": len(recs),
            "categories": cats,
            "sources": sources,
            "group_count": len(gids),
        }

    return {
        "seed": seed,
        "train_ratio": train_ratio,
        "train_records": train_records,
        "validation_records": val_records,
        "quarantine_records": quarantine_records,
        "summary": {
            "total_candidates": len(samples),
            "clean_candidates": len(clean_records),
            "train_count": len(train_records),
            "validation_count": len(val_records),
            "quarantine_count": len(quarantine_records),
            "train_groups": len(train_group_ids),
            "validation_groups": len(val_group_ids),
            "train_stats": _compute_stats(train_records),
            "validation_stats": _compute_stats(val_records),
            "quarantine_stats": _compute_stats(quarantine_records),
        },
    }
