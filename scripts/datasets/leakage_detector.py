"""CivicSense Benchmark Leakage Detection Tool.

Enforces zero-contamination invariants between the candidate training pool
and the frozen evaluation benchmark (datasets/benchmark_v1/):

1. Exact SHA-256 collision rejection
2. Upstream source record ID collision rejection
3. Canonical normalized source URL collision rejection
4. 64-bit dHash Hamming distance rejection (threshold: distance <= 6 bits)
5. Borderline perceptual match flagging (distance 7-10 bits)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.datasets.deduplicate_benchmark import hamming_distance  # noqa: E402

FROZEN_BENCHMARK_MANIFEST_HASH = (
    "e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b"
)
BENCHMARK_LEAKAGE_DHASH_THRESHOLD = 6
BORDERLINE_DHASH_UPPER_BOUND = 10
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
}


def normalize_url(url: str | None) -> str:
    """Normalize a web URL for canonical comparison without merging distinct assets."""
    if not url:
        return ""
    clean = url.strip()
    if not clean:
        return ""
    try:
        parsed = urllib.parse.urlparse(clean)
    except Exception:
        return clean.lower()

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip default ports
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Normalize path (remove trailing slash unless it's just '/')
    path = parsed.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Strip tracking query parameters while preserving resource parameters
    query_parts: list[tuple[str, str]] = []
    if parsed.query:
        for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
            if k.lower() not in TRACKING_PARAMS:
                query_parts.append((k, v))
    sorted_query = urllib.parse.urlencode(sorted(query_parts))

    return urllib.parse.urlunparse((scheme, netloc, path, "", sorted_query, ""))


@dataclass
class LeakageCheckResult:
    """Detailed result of checking a single candidate against the benchmark."""

    sample_id: str
    status: str  # "PASSED", "FAILED_EXACT_SHA256", "FAILED_SOURCE_ID", etc.
    passed: bool
    rejection_reason: str | None = None
    matched_benchmark_sample_id: str | None = None
    min_dhash_distance: int | None = None
    details: str | None = None
    is_borderline: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BenchmarkLeakageIndex:
    """Indexes the frozen 300-sample benchmark to audit candidate training samples."""

    def __init__(self, benchmark_dir: Path | str) -> None:
        self.benchmark_dir = Path(benchmark_dir)
        self.manifest_path = self.benchmark_dir / "manifest.json"
        self.dataset_jsonl_path = self.benchmark_dir / "benchmark_dataset.jsonl"

        self.benchmark_hashes: dict[str, str] = {}  # sha256 -> sample_id
        self.benchmark_source_ids: dict[tuple[str, str], str] = {}  # (src_name, src_rec_id) -> sample_id
        self.benchmark_urls: dict[str, str] = {}  # normalized_url -> sample_id
        self.benchmark_dhashes: list[tuple[str, str]] = []  # (sample_id, dhash_hex)
        self.is_manifest_verified: bool = False

        self._load_and_index()

    def _load_and_index(self) -> None:
        """Load benchmark dataset and verify manifest integrity."""
        if not self.dataset_jsonl_path.exists():
            raise FileNotFoundError(f"Benchmark dataset missing: {self.dataset_jsonl_path}")

        # 1. Verify benchmark integrity hash
        if self.dataset_jsonl_path.exists():
            jsonl_bytes = self.dataset_jsonl_path.read_bytes()
            computed_hash = hashlib.sha256(jsonl_bytes).hexdigest()
            self.is_manifest_verified = (computed_hash == FROZEN_BENCHMARK_MANIFEST_HASH)
            if self.manifest_path.exists():
                manifest_data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                if manifest_data.get("integrity_hash") != FROZEN_BENCHMARK_MANIFEST_HASH:
                    self.is_manifest_verified = False

        # 2. Index all benchmark records
        with open(self.dataset_jsonl_path, encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                record = json.loads(line_str)
                sample_id = record["sample_id"]
                sha256 = record.get("sha256", "").lower()
                source_dataset = record.get("source_dataset", "").lower()
                source_record_id = str(record.get("source_record_id", "")).strip()
                phash = record.get("phash", "").lower()

                if sha256:
                    self.benchmark_hashes[sha256] = sample_id
                if source_dataset and source_record_id:
                    self.benchmark_source_ids[(source_dataset, source_record_id)] = sample_id

                meta = record.get("metadata_json", {})
                source_url = meta.get("source_url") or record.get("license_url")
                norm_url = normalize_url(source_url)
                if norm_url and norm_url not in {"http://www.opendefinition.org/licenses/odc-pddl"}:
                    self.benchmark_urls[norm_url] = sample_id

                if phash:
                    self.benchmark_dhashes.append((sample_id, phash))

    @property
    def sample_count(self) -> int:
        return len(self.benchmark_hashes)

    def check_candidate(
        self,
        sample_id: str,
        sha256: str,
        source_name: str,
        source_record_id: str,
        source_url: str | None = None,
        dhash: str | None = None,
    ) -> LeakageCheckResult:
        """Evaluate a single candidate sample against all benchmark leakage invariants."""
        sha256_clean = sha256.lower().strip()
        source_name_clean = source_name.lower().strip()
        source_rec_clean = str(source_record_id).strip()
        norm_candidate_url = normalize_url(source_url)
        dhash_clean = dhash.lower().strip() if dhash else None

        # 1. Exact SHA-256 Collision Check
        if sha256_clean in self.benchmark_hashes:
            bm_id = self.benchmark_hashes[sha256_clean]
            return LeakageCheckResult(
                sample_id=sample_id,
                status="FAILED_EXACT_SHA256",
                passed=False,
                rejection_reason="Exact cryptographic SHA-256 collision with benchmark sample",
                matched_benchmark_sample_id=bm_id,
                details=f"SHA-256 {sha256_clean} matches benchmark sample {bm_id}",
            )

        # 2. Upstream Source Record ID Collision Check
        source_key = (source_name_clean, source_rec_clean)
        if source_key in self.benchmark_source_ids:
            bm_id = self.benchmark_source_ids[source_key]
            return LeakageCheckResult(
                sample_id=sample_id,
                status="FAILED_SOURCE_ID",
                passed=False,
                rejection_reason="Source dataset and source record ID collision with benchmark sample",
                matched_benchmark_sample_id=bm_id,
                details=f"Source ({source_name_clean}, {source_rec_clean}) matches benchmark sample {bm_id}",
            )

        # 3. Canonical Normalized Source URL Collision Check
        if norm_candidate_url and norm_candidate_url in self.benchmark_urls:
            # Only match if URL is a direct asset link or specific record URL
            bm_id = self.benchmark_urls[norm_candidate_url]
            return LeakageCheckResult(
                sample_id=sample_id,
                status="FAILED_SOURCE_URL",
                passed=False,
                rejection_reason="Canonical source asset URL collision with benchmark sample",
                matched_benchmark_sample_id=bm_id,
                details=f"URL {norm_candidate_url} matches benchmark sample {bm_id}",
            )

        # 4. Perceptual 64-bit dHash Hamming Distance Check
        min_dist: int | None = None
        closest_bm_id: str | None = None

        if dhash_clean and len(dhash_clean) == 16:
            for bm_id, bm_dhash in self.benchmark_dhashes:
                if len(bm_dhash) == 16:
                    dist = hamming_distance(dhash_clean, bm_dhash)
                    if min_dist is None or dist < min_dist:
                        min_dist = dist
                        closest_bm_id = bm_id

            if min_dist is not None and min_dist <= BENCHMARK_LEAKAGE_DHASH_THRESHOLD:
                return LeakageCheckResult(
                    sample_id=sample_id,
                    status="FAILED_DHASH_NEAR_DUPLICATE",
                    passed=False,
                    rejection_reason=(
                        f"Perceptual near-duplicate: dHash Hamming distance {min_dist} <= "
                        f"{BENCHMARK_LEAKAGE_DHASH_THRESHOLD} to benchmark sample {closest_bm_id}"
                    ),
                    matched_benchmark_sample_id=closest_bm_id,
                    min_dhash_distance=min_dist,
                    details=(
                        f"Candidate dHash {dhash_clean} has Hamming distance {min_dist} "
                        f"to benchmark sample {closest_bm_id}"
                    ),
                )

        # 5. Borderline Perceptual Warning
        is_borderline = False
        if min_dist is not None and min_dist <= BORDERLINE_DHASH_UPPER_BOUND:
            is_borderline = True

        return LeakageCheckResult(
            sample_id=sample_id,
            status="PASSED",
            passed=True,
            min_dhash_distance=min_dist,
            matched_benchmark_sample_id=closest_bm_id if is_borderline else None,
            is_borderline=is_borderline,
            details=f"Passed all leakage checks. Nearest benchmark distance: {min_dist} bits",
        )

    def audit_candidates(
        self, candidates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Audit an entire candidate pool and generate a comprehensive leakage report."""
        passed_count = 0
        rejected_count = 0
        rejection_breakdown: dict[str, int] = {
            "FAILED_EXACT_SHA256": 0,
            "FAILED_SOURCE_ID": 0,
            "FAILED_SOURCE_URL": 0,
            "FAILED_DHASH_NEAR_DUPLICATE": 0,
        }
        rejected_samples: list[dict[str, Any]] = []
        borderline_samples: list[dict[str, Any]] = []
        distance_distribution: dict[int, int] = {}

        for cand in candidates:
            res = self.check_candidate(
                sample_id=str(cand.get("sample_id", "")),
                sha256=str(cand.get("sha256", "")),
                source_name=str(cand.get("source_name", cand.get("source_dataset", ""))),
                source_record_id=str(cand.get("source_record_id", "")),
                source_url=cand.get("source_url"),
                dhash=cand.get("dhash") or cand.get("phash"),
            )

            if res.min_dhash_distance is not None:
                d = res.min_dhash_distance
                distance_distribution[d] = distance_distribution.get(d, 0) + 1

            if res.passed:
                passed_count += 1
                if res.is_borderline:
                    borderline_samples.append(res.to_dict())
            else:
                rejected_count += 1
                rejection_breakdown[res.status] = (
                    rejection_breakdown.get(res.status, 0) + 1
                )
                rejected_samples.append(res.to_dict())

        return {
            "audit_timestamp": json.dumps(
                __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
            ).strip('"'),
            "benchmark_sample_count": self.sample_count,
            "benchmark_manifest_hash_verified": self.is_manifest_verified,
            "total_candidates_checked": len(candidates),
            "total_passed": passed_count,
            "total_rejected": rejected_count,
            "rejection_breakdown": rejection_breakdown,
            "borderline_samples_count": len(borderline_samples),
            "rejected_samples": rejected_samples,
            "borderline_samples": borderline_samples,
            "dhash_distance_histogram": {
                str(k): v for k, v in sorted(distance_distribution.items())
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="CivicSense Benchmark Leakage Detector")
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=repo_root / "datasets" / "benchmark_v1",
        help="Path to frozen benchmark directory",
    )
    parser.add_argument(
        "--candidates-file",
        type=Path,
        required=True,
        help="Path to candidates jsonl or json file",
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        default=None,
        help="Path to write JSON leakage report",
    )
    args = parser.parse_args()

    detector = BenchmarkLeakageIndex(args.benchmark_dir)

    candidates: list[dict[str, Any]] = []
    if args.candidates_file.suffix == ".jsonl":
        with open(args.candidates_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    candidates.append(json.loads(line))
    else:
        with open(args.candidates_file, encoding="utf-8") as f:
            candidates = json.load(f)

    report = detector.audit_candidates(candidates)

    if args.output_report:
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Leakage report written to: {args.output_report}")

    print(f"Checked: {report['total_candidates_checked']} | Passed: {report['total_passed']} | Rejected: {report['total_rejected']}")


if __name__ == "__main__":
    main()
