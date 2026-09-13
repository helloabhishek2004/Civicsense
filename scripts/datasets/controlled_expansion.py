"""CivicSense Controlled Training Dataset Expansion Tool.

Safely discovers and acquires targeted candidate samples for deficient categories:
- Enforces DRY-RUN by default (requires --execute).
- Filters by source (--source) and canonical category (--category).
- Pre-download and post-download benchmark leakage defense (BenchmarkLeakageIndex).
- Rate limiting and exponential backoff retry logic.
- Writes raw candidate records exclusively into datasets/raw/<source>/ (never directly into clean splits).
- Produces auditable acquisition manifests.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
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
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB limit


def fetch_url_with_retry(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SEC,
    max_retries: int = DEFAULT_MAX_RETRIES,
    delay_sec: float = DEFAULT_DELAY_SEC,
) -> bytes:
    """Fetch URL bytes with exponential backoff and rate-limiting delay."""
    time.sleep(delay_sec)
    headers = {"User-Agent": "CivicSense-Research/1.0 (Controlled-Expansion-Audit)"}
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


class ControlledExpansionRunner:
    """Orchestrator for rate-limited, leakage-checked dataset expansion."""

    def __init__(
        self,
        raw_dir: Path,
        benchmark_dir: Path,
        delay_sec: float = DEFAULT_DELAY_SEC,
        max_retries: int = DEFAULT_MAX_RETRIES,
        execute: bool = False,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.benchmark_dir = Path(benchmark_dir)
        self.delay_sec = delay_sec
        self.max_retries = max_retries
        self.execute = execute

        self.leakage_index = BenchmarkLeakageIndex(self.benchmark_dir)

    def acquire_boston311_candidates(
        self,
        target_category: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Query Boston 311 CKAN API for deficient category and acquire non-leaked samples."""
        query_map = {
            "Pothole": "Request for Pothole Repair",
            "Road Damage": "Sidewalk Repair (Make Safe)",
            "Garbage": "Illegal Dumping",
            "Other": "Poor Conditions of Property",
            "Streetlight": "Parks Lighting/Electrical Issues",
        }
        if target_category not in query_map:
            return {
                "source": "boston311",
                "category": target_category,
                "status": "SKIPPED_UNSUPPORTED_CATEGORY",
            }

        search_term = query_map[target_category]
        target_dir = self.raw_dir / "boston311"
        images_dir = target_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        api_url = (
            "https://data.boston.gov/api/3/action/datastore_search?"
            "resource_id=2f9b31d0-9941-4545-ba37-3367b663b7fd&limit=100&"
            + urllib.parse.urlencode({"q": search_term})
        )

        plan: dict[str, Any] = {
            "source": "boston311",
            "category": target_category,
            "search_term": search_term,
            "target_limit": limit,
            "mode": "EXECUTE" if self.execute else "DRY_RUN",
            "evaluated_records": 0,
            "pre_leakage_skips": 0,
            "acquired_count": 0,
            "candidates": [],
        }

        if not self.execute:
            return plan

        # Fetch CKAN query results
        resp_bytes = fetch_url_with_retry(
            api_url,
            timeout=DEFAULT_TIMEOUT_SEC,
            max_retries=self.max_retries,
            delay_sec=self.delay_sec,
        )
        records = json.loads(resp_bytes.decode("utf-8")).get("result", {}).get("records", [])

        # Load existing raw samples to avoid re-fetching
        raw_samples_file = target_dir / "raw_samples.json"
        existing_raw = []
        existing_rec_ids = set()
        if raw_samples_file.exists():
            existing_raw = json.loads(raw_samples_file.read_text(encoding="utf-8"))
            existing_rec_ids = {str(s.get("source_record_id")) for s in existing_raw}

        acquired = 0
        for rec in records:
            if acquired >= limit:
                break
            plan["evaluated_records"] += 1
            rec_id = str(rec.get("service_request_id") or rec.get("_id"))
            img_url = rec.get("submittedphoto")

            if not img_url or not img_url.startswith("http"):
                continue
            if rec_id in existing_rec_ids:
                continue

            # 1. Pre-download Leakage Check
            pre_check = self.leakage_index.check_candidate(
                sample_id=f"bost_{rec_id}",
                sha256="",  # Not yet downloaded
                source_name="boston311",
                source_record_id=rec_id,
                source_url=img_url,
            )
            if not pre_check.passed:
                plan["pre_leakage_skips"] += 1
                continue

            # 2. Download Image Bytes safely
            try:
                img_data = fetch_url_with_retry(
                    img_url,
                    timeout=DEFAULT_TIMEOUT_SEC,
                    max_retries=self.max_retries,
                    delay_sec=self.delay_sec,
                )
            except Exception as err:
                print(f"Warning: Failed to download {img_url}: {err}")
                continue

            # 3. Save to disk and validate
            file_name = f"boston311_{rec_id}.jpg"
            img_dest = images_dir / file_name
            img_dest.write_bytes(img_data)

            val_res = validate_image_file(img_dest)
            if not val_res.is_valid:
                img_dest.unlink(missing_ok=True)
                continue

            # 4. Post-download Full Leakage Check (SHA-256 and dHash)
            post_check = self.leakage_index.check_candidate(
                sample_id=f"bost_{rec_id}",
                sha256=val_res.sha256,
                source_name="boston311",
                source_record_id=rec_id,
                source_url=img_url,
                dhash=val_res.phash,
            )
            if not post_check.passed:
                img_dest.unlink(missing_ok=True)
                plan["pre_leakage_skips"] += 1
                continue

            # Append to raw samples record
            sample_entry = {
                "sample_id": f"pilot_bost311_{rec_id}",
                "source_dataset": "boston311",
                "source_record_id": rec_id,
                "original_category": search_term,
                "canonical_category": target_category,
                "text_description": rec.get("type", search_term),
                "image_rel_path": f"boston311/images/{file_name}",
                "license": "ODC-PDDL",
                "license_url": "http://www.opendefinition.org/licenses/odc-pddl",
                "attribution": "City of Boston, Analyze Boston Open Data / 311 Service Requests",
                "source_url": img_url,
                "verification_level": "source_verified",
                "visual_relevance": "direct_issue_visible",
            }
            existing_raw.append(sample_entry)
            existing_rec_ids.add(rec_id)
            plan["candidates"].append(sample_entry)
            acquired += 1

        plan["acquired_count"] = acquired
        if acquired > 0:
            raw_samples_file.write_text(json.dumps(existing_raw, indent=2), encoding="utf-8")

        return plan


def main() -> None:
    parser = argparse.ArgumentParser(description="CivicSense Controlled Dataset Expansion Runner")
    parser.add_argument("--source", type=str, default="boston311", help="Target source name")
    parser.add_argument("--category", type=str, default="Pothole", help="Target canonical category")
    parser.add_argument("--limit", type=int, default=10, help="Max clean candidates to acquire")
    parser.add_argument("--delay-sec", type=float, default=DEFAULT_DELAY_SEC, help="Request rate-limit delay")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help="Max retry attempts")
    parser.add_argument("--execute", action="store_true", help="Execute network requests (default: dry-run)")
    args = parser.parse_args()

    raw_dir = repo_root / "datasets" / "raw"
    bm_dir = repo_root / "datasets" / "benchmark_v1"

    runner = ControlledExpansionRunner(
        raw_dir=raw_dir,
        benchmark_dir=bm_dir,
        delay_sec=args.delay_sec,
        max_retries=args.max_retries,
        execute=args.execute,
    )

    if args.source == "boston311":
        plan = runner.acquire_boston311_candidates(target_category=args.category, limit=args.limit)
        print(json.dumps(plan, indent=2))
    else:
        print(f"Source '{args.source}' supported via dry-run and configuration.")


if __name__ == "__main__":
    main()
