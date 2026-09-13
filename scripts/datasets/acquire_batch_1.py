"""CivicSense Phase 3.3 Step 4 Controlled Acquisition Execution Tool.

Acquires an auditable, rate-limited, leakage-screened batch of candidate samples
for deficient categories (Pothole and Other with explicit subtypes):
- Enforces DRY-RUN by default (requires --execute).
- Queries Boston 311 CKAN Datastore API with pagination.
- Enforces pre-download and post-download benchmark leakage checks.
- Enforces PIL decoding, decompression bomb checks, dimension constraints.
- Writes acquired files exclusively into datasets/raw/boston311/images/.
- Writes candidate acquisition manifest to datasets/training_v1/acquisition/batch_1_manifest.json.
- Updates datasets/raw/boston311/raw_samples.json for downstream curation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure repository root and backend are on sys.path
repo_root = Path(__file__).resolve().parents[2]
backend_path = repo_root / "backend"
for p in (str(repo_root), str(backend_path)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.datasets.leakage_detector import BenchmarkLeakageIndex  # noqa: E402
from scripts.datasets.validate_images import validate_image_file  # noqa: E402

DEFAULT_DELAY_SEC = 0.5
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SEC = 15
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB per image

# Boston 311 Datastore 2026 Resource ID
BOSTON_311_RESOURCE_2026 = "1a0b420d-99f1-4887-9851-990b2a5a6e17"

BATCH_1_SPECIFICATION: list[dict[str, Any]] = [
    {
        "category": "Pothole",
        "query_type": "Request for Pothole Repair",
        "subtype": None,
        "target_count": 50,
        "initial_offset": 100,
    },
    {
        "category": "Other",
        "query_type": "Graffiti Removal",
        "subtype": "graffiti",
        "target_count": 20,
        "initial_offset": 100,
    },
    {
        "category": "Other",
        "query_type": "Poor Conditions of Property",
        "subtype": "other_documented_civic_defect",
        "target_count": 20,
        "initial_offset": 100,
    },
    {
        "category": "Other",
        "query_type": "Sidewalk Repair (Make Safe)",
        "subtype": "damaged_sidewalk",
        "target_count": 10,
        "initial_offset": 100,
    },
]


def fetch_url_with_retry(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SEC,
    max_retries: int = DEFAULT_MAX_RETRIES,
    delay_sec: float = DEFAULT_DELAY_SEC,
) -> bytes:
    """Fetch URL bytes with exponential backoff and rate-limiting delay."""
    time.sleep(delay_sec)
    headers = {"User-Agent": "CivicSense-Research/1.0 (Phase3.3-Controlled-Acquisition)"}
    req = urllib.request.Request(url, headers=headers)

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data: bytes = resp.read()
                if len(data) > MAX_IMAGE_BYTES:
                    raise ValueError(f"Image exceeds size cap ({len(data)} > {MAX_IMAGE_BYTES})")
                return data
        except Exception as err:
            last_err = err
            wait = delay_sec * (2**attempt)
            time.sleep(wait)

    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts: {last_err}")


class BatchAcquisitionRunner:
    """Orchestrates controlled acquisition of Batch 1 candidates."""

    def __init__(
        self,
        raw_dir: Path,
        benchmark_dir: Path,
        training_dir: Path,
        delay_sec: float = DEFAULT_DELAY_SEC,
        max_retries: int = DEFAULT_MAX_RETRIES,
        execute: bool = False,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.benchmark_dir = Path(benchmark_dir)
        self.training_dir = Path(training_dir)
        self.delay_sec = delay_sec
        self.max_retries = max_retries
        self.execute = execute

        self.leakage_index = BenchmarkLeakageIndex(self.benchmark_dir)
        self.boston_raw_dir = self.raw_dir / "boston311"
        self.images_dir = self.boston_raw_dir / "images"
        self.acquisition_dir = self.training_dir / "acquisition"

        self.existing_raw_samples: list[dict[str, Any]] = []
        self.existing_case_ids: set[str] = set()
        self._load_existing_raw()

    def _load_existing_raw(self) -> None:
        raw_file = self.boston_raw_dir / "raw_samples.json"
        if raw_file.exists():
            try:
                self.existing_raw_samples = json.loads(raw_file.read_text(encoding="utf-8"))
                for s in self.existing_raw_samples:
                    cid = str(s.get("source_record_id") or "")
                    if cid:
                        self.existing_case_ids.add(cid)
            except Exception as err:
                print(f"Warning: Failed to load existing raw samples: {err}")

    def run_dry_run(self) -> dict[str, Any]:
        """Execute pre-flight audit and generate dry-run plan."""
        plan_items: list[dict[str, Any]] = []
        total_target = 0

        for spec in BATCH_1_SPECIFICATION:
            total_target += spec["target_count"]
            plan_items.append({
                "category": spec["category"],
                "subtype": spec["subtype"],
                "query_type": spec["query_type"],
                "target_count": spec["target_count"],
                "source": "boston311",
                "license": "ODC-PDDL",
                "license_url": "http://www.opendefinition.org/licenses/odc-pddl",
                "rate_limit": f"{self.delay_sec}s per request, max {self.max_retries} retries",
            })

        estimated_mb = total_target * 1.3  # Average ~1.3 MB per image based on Phase 3.3.3 audit

        dry_run_report = {
            "mode": "DRY_RUN",
            "timestamp": datetime.now(UTC).isoformat(),
            "target_total_candidates": total_target,
            "category_targets": {
                "Pothole": 50,
                "Other": 50,
            },
            "subtype_targets": {
                "graffiti": 20,
                "other_documented_civic_defect": 20,
                "damaged_sidewalk": 10,
            },
            "source_distribution": {
                "boston311": total_target,
            },
            "estimated_storage_mb": round(estimated_mb, 1),
            "rate_limit_behavior": f"{self.delay_sec}s pause between HTTP calls; bounded retries {self.max_retries}",
            "licensing_coverage": {
                "boston311": {
                    "license": "ODC-PDDL",
                    "license_scope": "dataset",
                    "status": "fully_compliant",
                    "commercial_use_allowed": True,
                    "redistribution_allowed": True,
                }
            },
            "benchmark_overlap_defense": {
                "pre_download_check": "Active (BenchmarkLeakageIndex)",
                "post_download_sha256": "Active",
                "post_download_dhash_threshold": "Hamming distance <= 6 strictly unlinked",
            },
            "staging_path": str(self.images_dir),
            "clean_splits_modified": False,
            "specifications": plan_items,
        }
        return dry_run_report

    def run_acquisition(self) -> dict[str, Any]:
        """Execute controlled network acquisition."""
        if not self.execute:
            return self.run_dry_run()

        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.acquisition_dir.mkdir(parents=True, exist_ok=True)

        batch_manifest: dict[str, Any] = {
            "batch_id": "batch_1_pothole_other",
            "execution_timestamp": datetime.now(UTC).isoformat(),
            "source_dataset": "boston311",
            "target_summary": {
                "Pothole": 50,
                "Other": 50,
            },
            "acquired_summary": {
                "Pothole": 0,
                "Other": 0,
            },
            "acquired_by_subtype": {},
            "quarantined_count": 0,
            "leakage_rejections": 0,
            "duplicate_skips": 0,
            "network_errors": 0,
            "candidates": [],
            "quarantined_candidates": [],
        }

        total_acquired = 0

        for spec in BATCH_1_SPECIFICATION:
            canonical_cat = spec["category"]
            query_type = spec["query_type"]
            subtype = spec["subtype"]
            target_count = spec["target_count"]
            current_acquired_for_spec = 0
            offset = spec["initial_offset"]

            print(f"Acquiring {target_count} candidates for {canonical_cat} (subtype: {subtype}, query: '{query_type}')...")

            while current_acquired_for_spec < target_count:
                filters = json.dumps({"type": query_type})
                api_url = (
                    f"https://data.boston.gov/api/3/action/datastore_search?"
                    f"resource_id={BOSTON_311_RESOURCE_2026}&limit=100&offset={offset}&"
                    f"filters={urllib.parse.quote(filters)}"
                )

                try:
                    resp_bytes = fetch_url_with_retry(
                        api_url,
                        timeout=DEFAULT_TIMEOUT_SEC,
                        max_retries=self.max_retries,
                        delay_sec=self.delay_sec,
                    )
                    records = json.loads(resp_bytes.decode("utf-8")).get("result", {}).get("records", [])
                except Exception as err:
                    print(f"Error querying CKAN at offset {offset}: {err}")
                    batch_manifest["network_errors"] += 1
                    break

                if not records:
                    print(f"No more records returned at offset {offset}.")
                    break

                offset += len(records)

                for rec in records:
                    if current_acquired_for_spec >= target_count:
                        break

                    case_id = str(rec.get("case_enquiry_id") or rec.get("_id") or "")
                    if not case_id or case_id in self.existing_case_ids:
                        batch_manifest["duplicate_skips"] += 1
                        continue

                    photo_url = rec.get("closed_photo") or rec.get("submittedphoto")
                    if not photo_url or not photo_url.startswith("http"):
                        continue

                    clean_url = photo_url.split("|")[0].split("#")[0].strip()

                    # 1. Pre-download Leakage Check
                    sample_id = f"bost_{case_id}"
                    pre_check = self.leakage_index.check_candidate(
                        sample_id=sample_id,
                        sha256="",
                        source_name="boston311",
                        source_record_id=case_id,
                        source_url=clean_url,
                    )
                    if not pre_check.passed:
                        batch_manifest["leakage_rejections"] += 1
                        batch_manifest["quarantined_candidates"].append({
                            "sample_id": sample_id,
                            "case_id": case_id,
                            "reason": f"Pre-download leakage rejection: {pre_check.rejection_reason}",
                            "details": pre_check.details,
                        })
                        continue

                    # 2. Safe Download into Staging
                    file_name = f"boston311_{case_id}.jpg"
                    img_dest = self.images_dir / file_name

                    try:
                        img_bytes = fetch_url_with_retry(
                            clean_url,
                            timeout=DEFAULT_TIMEOUT_SEC,
                            max_retries=self.max_retries,
                            delay_sec=self.delay_sec,
                        )
                    except Exception as err:
                        print(f"Failed to download photo {clean_url}: {err}")
                        batch_manifest["network_errors"] += 1
                        continue

                    # 3. Save to disk temporarily and validate
                    img_dest.write_bytes(img_bytes)
                    val_res = validate_image_file(img_dest)

                    if not val_res.is_valid:
                        img_dest.unlink(missing_ok=True)
                        batch_manifest["quarantined_count"] += 1
                        batch_manifest["quarantined_candidates"].append({
                            "sample_id": sample_id,
                            "case_id": case_id,
                            "reason": f"Image validation failed: {val_res.rejection_reason}",
                        })
                        continue

                    # 4. Post-download Full Leakage Check (SHA-256 and dHash <= 6)
                    post_check = self.leakage_index.check_candidate(
                        sample_id=sample_id,
                        sha256=val_res.sha256,
                        source_name="boston311",
                        source_record_id=case_id,
                        source_url=clean_url,
                        dhash=val_res.phash,
                    )
                    if not post_check.passed:
                        img_dest.unlink(missing_ok=True)
                        batch_manifest["leakage_rejections"] += 1
                        batch_manifest["quarantined_candidates"].append({
                            "sample_id": sample_id,
                            "case_id": case_id,
                            "reason": f"Post-download leakage rejection: {post_check.rejection_reason}",
                            "min_dhash_distance": post_check.min_dhash_distance,
                        })
                        continue

                    # 5. Success: Construct Candidate Provenance Record
                    candidate_entry = {
                        "sample_id": f"pilot_bost311_{case_id}",
                        "source_dataset": "boston311",
                        "source_name": "boston311",
                        "source_record_id": case_id,
                        "original_category": query_type,
                        "canonical_category": canonical_cat,
                        "subtype": subtype,
                        "text_description": rec.get("type", query_type),
                        "image_rel_path": f"boston311/images/{file_name}",
                        "license": "ODC-PDDL",
                        "license_url": "http://www.opendefinition.org/licenses/odc-pddl",
                        "attribution": "City of Boston, Analyze Boston Open Data / 311 Service Requests",
                        "source_url": clean_url,
                        "canonical_url": clean_url,
                        "acquisition_timestamp": datetime.now(UTC).isoformat(),
                        "acquisition_method": "ckan_api_controlled_download",
                        "original_metadata": {
                            "case_enquiry_id": rec.get("case_enquiry_id"),
                            "open_dt": rec.get("open_dt"),
                            "closed_dt": rec.get("closed_dt"),
                            "type": rec.get("type"),
                            "location": rec.get("location"),
                            "neighborhood": rec.get("neighborhood"),
                            "latitude": rec.get("latitude"),
                            "longitude": rec.get("longitude"),
                        },
                        "grouping_metadata": {
                            "group_id": f"grp_bost_{case_id}",
                            "location": rec.get("location"),
                        },
                        "verification_level": "source_verified",
                        "visual_relevance": "direct_issue_visible",
                        "width": val_res.width,
                        "height": val_res.height,
                        "file_size_bytes": val_res.file_size_bytes,
                        "sha256": val_res.sha256,
                        "dhash": val_res.phash,
                        "quality_flags": list(val_res.warnings),
                    }

                    # Append to tracking
                    self.existing_raw_samples.append(candidate_entry)
                    self.existing_case_ids.add(case_id)
                    batch_manifest["candidates"].append(candidate_entry)

                    batch_manifest["acquired_summary"][canonical_cat] += 1
                    if subtype:
                        batch_manifest["acquired_by_subtype"][subtype] = (
                            batch_manifest["acquired_by_subtype"].get(subtype, 0) + 1
                        )

                    current_acquired_for_spec += 1
                    total_acquired += 1

                    if total_acquired % 10 == 0:
                        print(f"Acquired {total_acquired} candidates so far...")

        # Save updated raw_samples.json
        raw_samples_file = self.boston_raw_dir / "raw_samples.json"
        raw_samples_file.write_text(json.dumps(self.existing_raw_samples, indent=2), encoding="utf-8")

        # Save batch acquisition manifest
        batch_manifest_file = self.acquisition_dir / "batch_1_manifest.json"
        batch_manifest_file.write_text(json.dumps(batch_manifest, indent=2), encoding="utf-8")

        print(f"\nAcquisition complete! Total acquired: {total_acquired}")
        print(f"Pothole: {batch_manifest['acquired_summary']['Pothole']}")
        print(f"Other: {batch_manifest['acquired_summary']['Other']}")
        print(f"Subtypes: {batch_manifest['acquired_by_subtype']}")
        print(f"Leakage rejections: {batch_manifest['leakage_rejections']}")
        print(f"Quarantined/Failed: {batch_manifest['quarantined_count']}")

        return batch_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="CivicSense Phase 3.3 Step 4 Controlled Acquisition Runner")
    parser.add_argument("--execute", action="store_true", help="Execute real network download and staging (default: dry-run)")
    parser.add_argument("--delay-sec", type=float, default=DEFAULT_DELAY_SEC, help="Per-request delay in seconds")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help="Max retry attempts")
    args = parser.parse_args()

    raw_dir = repo_root / "datasets" / "raw"
    benchmark_dir = repo_root / "datasets" / "benchmark_v1"
    training_dir = repo_root / "datasets" / "training_v1"

    runner = BatchAcquisitionRunner(
        raw_dir=raw_dir,
        benchmark_dir=benchmark_dir,
        training_dir=training_dir,
        delay_sec=args.delay_sec,
        max_retries=args.max_retries,
        execute=args.execute,
    )

    if not args.execute:
        plan = runner.run_dry_run()
        print(json.dumps(plan, indent=2))
    else:
        runner.run_acquisition()
        print(f"Saved batch manifest to {runner.acquisition_dir / 'batch_1_manifest.json'}")


if __name__ == "__main__":
    main()
