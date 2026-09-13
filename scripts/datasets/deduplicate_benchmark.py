"""CivicSense Benchmark Deduplication.

Implements two-level deduplication:
1. Exact duplicate detection via cryptographic SHA-256 hash.
2. Near-duplicate detection via 64-bit difference hash (dHash) and Hamming distance threshold.

Preserves duplicate provenance without destructive file deletion.
"""

from dataclasses import asdict, dataclass, field
from typing import Any


def hamming_distance(hex_hash1: str, hex_hash2: str) -> int:
    """Calculate the Hamming bit distance between two hexadecimal hash strings."""
    val1 = int(hex_hash1, 16)
    val2 = int(hex_hash2, 16)
    return bin(val1 ^ val2).count("1")


@dataclass
class DeduplicationRecord:
    sample_id: str
    duplicate_type: str  # "UNIQUE", "EXACT_DUPLICATE", "NEAR_DUPLICATE"
    duplicate_group_id: str | None = None
    similarity_distance: int = 0
    matched_with_sample_id: str | None = None


@dataclass
class DeduplicationReport:
    total_input_samples: int = 0
    unique_samples_count: int = 0
    exact_duplicates_count: int = 0
    near_duplicates_count: int = 0
    retained_sample_ids: list[str] = field(default_factory=list)
    discarded_sample_ids: list[str] = field(default_factory=list)
    duplicate_records: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def deduplicate_exact(
    samples: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Perform exact deduplication using SHA-256 hash."""
    seen_hashes: dict[str, dict[str, Any]] = {}
    unique: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []

    sorted_samples = sorted(samples, key=lambda s: str(s.get("sample_id", "")))

    for sample in sorted_samples:
        sha256 = sample.get("sha256")
        if not sha256:
            unique.append(sample)
            continue

        if sha256 in seen_hashes:
            winner = seen_hashes[sha256]
            sample_copy = dict(sample)
            sample_copy["duplicate_group_id"] = winner.get("sample_id")
            sample_copy["duplicate_type"] = "EXACT_DUPLICATE"
            duplicates.append(sample_copy)
        else:
            seen_hashes[sha256] = sample
            unique.append(sample)

    return unique, duplicates


def deduplicate_perceptual(
    samples: list[dict[str, Any]],
    threshold: int = 4,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Perform near-duplicate deduplication using perceptual hash (dHash) and Hamming distance."""
    unique: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []

    sorted_samples = sorted(samples, key=lambda s: str(s.get("sample_id", "")))

    for candidate in sorted_samples:
        candidate_phash = candidate.get("phash")
        if not candidate_phash:
            unique.append(candidate)
            continue

        matched_winner: dict[str, Any] | None = None
        min_dist = 999

        for kept in unique:
            kept_phash = kept.get("phash")
            if not kept_phash:
                continue
            try:
                dist = hamming_distance(candidate_phash, kept_phash)
                if dist <= threshold and dist < min_dist:
                    min_dist = dist
                    matched_winner = kept
            except Exception:
                continue

        if matched_winner is not None:
            cand_copy = dict(candidate)
            cand_copy["duplicate_group_id"] = matched_winner.get("sample_id")
            cand_copy["duplicate_type"] = "NEAR_DUPLICATE"
            cand_copy["hamming_distance"] = min_dist
            duplicates.append(cand_copy)
        else:
            unique.append(candidate)

    return unique, duplicates


def run_deduplication(
    samples: list[dict[str, Any]],
    phash_threshold: int = 4,
) -> tuple[list[dict[str, Any]], DeduplicationReport]:
    """Execute two-phase deduplication (exact SHA-256 followed by near-duplicate dHash)."""
    total = len(samples)

    after_exact, exact_dupes = deduplicate_exact(samples)
    retained, near_dupes = deduplicate_perceptual(after_exact, threshold=phash_threshold)

    all_dupes: list[dict[str, Any]] = []
    for d in exact_dupes:
        all_dupes.append({
            "sample_id": d.get("sample_id"),
            "duplicate_type": "EXACT_DUPLICATE",
            "duplicate_group_id": d.get("duplicate_group_id"),
            "sha256": d.get("sha256"),
            "phash": d.get("phash"),
        })
    for d in near_dupes:
        all_dupes.append({
            "sample_id": d.get("sample_id"),
            "duplicate_type": "NEAR_DUPLICATE",
            "duplicate_group_id": d.get("duplicate_group_id"),
            "sha256": d.get("sha256"),
            "phash": d.get("phash"),
            "hamming_distance": d.get("hamming_distance"),
        })

    report = DeduplicationReport(
        total_input_samples=total,
        unique_samples_count=len(retained),
        exact_duplicates_count=len(exact_dupes),
        near_duplicates_count=len(near_dupes),
        retained_sample_ids=[str(s.get("sample_id")) for s in retained],
        discarded_sample_ids=[str(d.get("sample_id")) for d in all_dupes],
        duplicate_records=all_dupes,
    )

    return retained, report
