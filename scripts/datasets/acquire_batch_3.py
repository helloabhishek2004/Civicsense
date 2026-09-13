"""CivicSense Phase 3.3 Step 6 Accelerated Controlled Acquisition Batch 3.

Acquires an auditable, rate-limited, leakage-screened batch of candidate samples
targeting the remaining class deficits toward the 600-sample Minimum Training Gate:
  - Garbage       (target: 45 candidates, remaining deficit: 34)
  - Pothole       (target: 55 candidates, remaining deficit: 50)
  - Other         (target: 55 candidates, remaining deficit: 50)
  - Water Leakage (target: 55 candidates, remaining deficit: 47)
  - Road Damage   (target: 50 candidates, remaining deficit: 43)
  - Streetlight   (target: 50 candidates, remaining deficit: 43)

Total Planned Candidates: 310

Multi-Source Strategy:
  - Boston 311 CKAN API:
      - Pothole: Request for Pothole Repair (offset 150+)
      - Garbage: Improper Storage of Trash (offset 60+), Illegal Dumping (offset 30+)
      - Other: Graffiti Removal (graffiti, offset 25+), Poor Conditions of Property (blight, offset 25+)
  - Wikimedia Commons API:
      - Other: damaged road signs, fallen tree road blockages, damaged guardrails
      - Water Leakage: fresh burst pipe, municipal aqueduct, hydrant leak queries
      - Road Damage: fresh surface subsidence, rutting, frost heave, bitumen breakdown queries
      - Streetlight: fresh bent pole collision, downed light pole, shattered luminaire queries

Enforcement:
  - DRY-RUN by default (requires --execute).
  - Dual-layer benchmark leakage defense (SHA-256 + dHash <= 6).
  - Cross-checks against all previous manifest entries, raw sources, and batch 1/2 manifests.
  - Intra-batch source-ID and SHA-256 deduplication.
  - PIL decoding, decompression bomb guard, dimension constraints.
  - Raw images staged strictly under datasets/raw/<source>/batch_3/images/.
  - Manifest written to datasets/training_v1/acquisition/batch_3_manifest.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

repo_root = Path(__file__).resolve().parents[2]
backend_path = repo_root / "backend"
for _p in (str(repo_root), str(backend_path)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.datasets.leakage_detector import BenchmarkLeakageIndex
from scripts.datasets.validate_images import validate_image_file

BATCH_ID = "batch_3_accelerated_dataset_completion"
DEFAULT_DELAY_SEC = 0.5
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SEC = 20
MAX_IMAGE_BYTES = 10 * 1024 * 1024

BOSTON_311_RESOURCE_2026 = "1a0b420d-99f1-4887-9851-990b2a5a6e17"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
WIKIMEDIA_USER_AGENT = (
    "CivicSense-Research/1.0 "
    "(https://github.com/helloabhishek2004/Civicsense; Batch3)"
)
ACCEPTED_LICENSE_KEYWORDS = ("CC", "PUBLIC DOMAIN", "PD-", "ODC", "CC0")

# ---------------------------------------------------------------------------
# Batch 3 Specifications
# ---------------------------------------------------------------------------

BATCH_3_BOSTON_SPECS: list[dict[str, Any]] = [
    {
        "category": "Pothole",
        "subtype": None,
        "query_type": "Request for Pothole Repair",
        "target_count": 55,
        "initial_offset": 150,
        "license": "ODC-PDDL",
        "license_url": "http://www.opendefinition.org/licenses/odc-pddl",
        "attribution": "City of Boston, Analyze Boston Open Data / 311 Service Requests",
        "source_name": "boston311",
        "batch_source_prefix": "bost_b3pothole",
    },
    {
        "category": "Garbage",
        "subtype": None,
        "query_type": "Improper Storage of Trash (Barrels)",
        "target_count": 30,
        "initial_offset": 60,
        "license": "ODC-PDDL",
        "license_url": "http://www.opendefinition.org/licenses/odc-pddl",
        "attribution": "City of Boston, Analyze Boston Open Data / 311 Service Requests",
        "source_name": "boston311",
        "batch_source_prefix": "bost_b3trash",
    },
    {
        "category": "Garbage",
        "subtype": None,
        "query_type": "Illegal Dumping",
        "target_count": 15,
        "initial_offset": 30,
        "license": "ODC-PDDL",
        "license_url": "http://www.opendefinition.org/licenses/odc-pddl",
        "attribution": "City of Boston, Analyze Boston Open Data / 311 Service Requests",
        "source_name": "boston311",
        "batch_source_prefix": "bost_b3dump",
    },
    {
        "category": "Other",
        "subtype": "graffiti",
        "query_type": "Graffiti Removal",
        "target_count": 20,
        "initial_offset": 25,
        "license": "ODC-PDDL",
        "license_url": "http://www.opendefinition.org/licenses/odc-pddl",
        "attribution": "City of Boston, Analyze Boston Open Data / 311 Service Requests",
        "source_name": "boston311",
        "batch_source_prefix": "bost_b3graffiti",
    },
    {
        "category": "Other",
        "subtype": "other_documented_civic_defect",
        "query_type": "Poor Conditions of Property",
        "target_count": 20,
        "initial_offset": 25,
        "license": "ODC-PDDL",
        "license_url": "http://www.opendefinition.org/licenses/odc-pddl",
        "attribution": "City of Boston, Analyze Boston Open Data / 311 Service Requests",
        "source_name": "boston311",
        "batch_source_prefix": "bost_b3property",
    },
]

WIKIMEDIA_OTHER_QUERIES_B3 = [
    "damaged road sign street",
    "fallen tree road blockage urban",
    "damaged guardrail roadway",
    "broken park bench vandalism",
    "damaged traffic barrier road",
    "bent traffic sign post",
    "vandalized public phone booth",
    "broken municipal trash bin street",
    "damaged bus stop shelter glass",
    "fallen tree blocking sidewalk",
    "damaged safety barrier highway",
    "bent street sign pole urban",
]

WIKIMEDIA_WATER_QUERIES_B3 = [
    "pipe burst flooding street urban",
    "water main repair road excavation",
    "hydrant gushing water street",
    "water pipeline damage outdoor municipal",
    "broken underground water pipe street",
    "water gushing roadway urban leak",
    "subsurface water main rupture road",
    "municipal aqueduct leakage road",
    "broken sprinkler public street flood",
    "water infrastructure rupture pavement",
    "water main blowout street asphalt",
    "fire hydrant collision water shooting",
    "street flooded water supply break",
]

WIKIMEDIA_ROAD_DAMAGE_QUERIES_B3 = [
    "road surface subsidence asphalt",
    "pavement rutting road damage urban",
    "severe alligator cracking road asphalt",
    "frost heave road damage pavement",
    "road shoulder erosion asphalt failure",
    "cracked bitumen roadway municipal",
    "road surface disintegration pavement",
    "road buckle damage heat asphalt",
    "longitudinal road pavement cracking",
    "asphalt road structural failure",
    "road collapse sinkhole urban street",
    "damaged road surface wear bitumen",
]

WIKIMEDIA_STREETLIGHT_QUERIES_B3 = [
    "damaged street lighting fixture pole",
    "bent light pole collision road street",
    "broken lamppost outdoor city public",
    "street lamp post knocked down accident",
    "vandalized public lamp fixture street",
    "traffic pole collision damage street",
    "downed light pole storm road",
    "street light fixture broken glass pole",
    "damaged highway light mast pole",
    "broken urban lantern post pavement",
    "cracked street light glass fixture",
    "bent lamppost car crash urban",
]

BATCH_3_WIKIMEDIA_SPECS: list[dict[str, Any]] = [
    {
        "category": "Other",
        "subtype": "other_documented_civic_defect",
        "source_name": "wikimedia_other",
        "source_dataset": "wikimedia_other",
        "id_prefix": "wmother_b3",
        "queries": WIKIMEDIA_OTHER_QUERIES_B3,
        "target_count": 15,
        "attribution_template": "{artist} via Wikimedia Commons",
        "raw_subdir": "wikimedia_other",
    },
    {
        "category": "Water Leakage",
        "subtype": None,
        "source_name": "wikimedia_water",
        "source_dataset": "wikimedia_water",
        "id_prefix": "wmwater_b3",
        "queries": WIKIMEDIA_WATER_QUERIES_B3,
        "target_count": 55,
        "attribution_template": "{artist} via Wikimedia Commons",
        "raw_subdir": "wikimedia_water",
    },
    {
        "category": "Road Damage",
        "subtype": None,
        "source_name": "wikimedia_road_damage",
        "source_dataset": "wikimedia_road_damage",
        "id_prefix": "wmroad_b3",
        "queries": WIKIMEDIA_ROAD_DAMAGE_QUERIES_B3,
        "target_count": 50,
        "attribution_template": "{artist} via Wikimedia Commons",
        "raw_subdir": "wikimedia_road_damage",
    },
    {
        "category": "Streetlight",
        "subtype": None,
        "source_name": "wikimedia_streetlight",
        "source_dataset": "wikimedia_streetlight",
        "id_prefix": "wmlight_b3",
        "queries": WIKIMEDIA_STREETLIGHT_QUERIES_B3,
        "target_count": 50,
        "attribution_template": "{artist} via Wikimedia Commons",
        "raw_subdir": "wikimedia_streetlight",
    },
]


def fetch_url_with_retry(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SEC,
    max_retries: int = DEFAULT_MAX_RETRIES,
    delay_sec: float = DEFAULT_DELAY_SEC,
    headers: dict[str, str] | None = None,
) -> bytes:
    """Fetch URL bytes with exponential backoff and rate-limiting delay."""
    time.sleep(delay_sec)
    req_headers: dict[str, str] = {
        "User-Agent": "CivicSense-Research/1.0 (Phase3.3-Batch3)"
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data: bytes = resp.read()
                if len(data) > MAX_IMAGE_BYTES:
                    raise ValueError(
                        f"Response exceeds size cap ({len(data)} > {MAX_IMAGE_BYTES})"
                    )
                return data
        except Exception as err:  # noqa: BLE001
            last_err = err
            wait = delay_sec * (2**attempt)
            time.sleep(wait)
    raise RuntimeError(
        f"Failed to fetch {url} after {max_retries} attempts: {last_err}"
    )


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text).strip()


class Batch3AcquisitionRunner:
    """Orchestrates accelerated acquisition of Batch 3 candidates."""

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
        self.acquisition_dir = self.training_dir / "acquisition"
        self.existing_source_ids: set[str] = set()
        self.existing_sha256s: set[str] = set()
        self._load_existing_records()

    def _load_existing_records(self) -> None:
        """Load all known source record IDs and SHA-256s from manifest and prior batches."""
        # 1. From manifest.jsonl
        manifest_path = self.training_dir / "manifest.jsonl"
        if manifest_path.exists():
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            rec = json.loads(line)
                            src_id = str(rec.get("source_record_id") or "")
                            sha = str(rec.get("sha256") or "")
                            if src_id:
                                self.existing_source_ids.add(src_id)
                            if sha and len(sha) == 64:
                                self.existing_sha256s.add(sha)
            except Exception as err:  # noqa: BLE001
                print(f"Warning: Failed to load manifest: {err}")

        # 2. From raw_samples.json in all raw dirs
        if self.raw_dir.exists():
            for src_dir in self.raw_dir.iterdir():
                if not src_dir.is_dir():
                    continue
                rs_file = src_dir / "raw_samples.json"
                if rs_file.exists():
                    try:
                        samples = json.loads(rs_file.read_text(encoding="utf-8"))
                        for s in samples:
                            sid = str(s.get("source_record_id") or "")
                            sha = str(s.get("sha256") or "")
                            if sid:
                                self.existing_source_ids.add(sid)
                            if sha and len(sha) == 64:
                                self.existing_sha256s.add(sha)
                    except Exception:  # noqa: BLE001, S110
                        pass

        # 3. From prior batch manifests
        if self.acquisition_dir.exists():
            for mf in self.acquisition_dir.glob("batch_*_manifest.json"):
                try:
                    data = json.loads(mf.read_text(encoding="utf-8"))
                    for cand in data.get("candidates", []):
                        srid = str(cand.get("source_record_id") or "")
                        sha = str(cand.get("sha256") or "")
                        if srid:
                            self.existing_source_ids.add(srid)
                        if sha and len(sha) == 64:
                            self.existing_sha256s.add(sha)
                except Exception:  # noqa: BLE001, S110
                    pass

    def run_dry_run(self) -> dict[str, Any]:
        """Execute pre-flight audit and generate dry-run plan."""
        boston_total = sum(s["target_count"] for s in BATCH_3_BOSTON_SPECS)
        wikimedia_total = sum(s["target_count"] for s in BATCH_3_WIKIMEDIA_SPECS)
        total_targets = boston_total + wikimedia_total

        cat_targets: dict[str, int] = {}
        for s in BATCH_3_BOSTON_SPECS:
            c = s["category"]
            cat_targets[c] = cat_targets.get(c, 0) + s["target_count"]
        for s in BATCH_3_WIKIMEDIA_SPECS:
            c = s["category"]
            cat_targets[c] = cat_targets.get(c, 0) + s["target_count"]

        plan: dict[str, Any] = {
            "mode": "DRY_RUN",
            "batch_id": BATCH_ID,
            "timestamp": datetime.now(UTC).isoformat(),
            "target_total_candidates": total_targets,
            "category_targets": cat_targets,
            "source_distribution": {
                "boston311": boston_total,
                "wikimedia_other": BATCH_3_WIKIMEDIA_SPECS[0]["target_count"],
                "wikimedia_water": BATCH_3_WIKIMEDIA_SPECS[1]["target_count"],
                "wikimedia_road_damage": BATCH_3_WIKIMEDIA_SPECS[2]["target_count"],
                "wikimedia_streetlight": BATCH_3_WIKIMEDIA_SPECS[3]["target_count"],
            },
            "estimated_storage_mb": round(total_targets * 1.2, 1),
            "rate_limit_behavior": (
                f"{self.delay_sec}s pause between HTTP calls; "
                f"max {self.max_retries} retries with exponential backoff"
            ),
            "licensing_coverage": {
                "boston311": "ODC-PDDL",
                "wikimedia_commons": "CC-BY / CC0 / Public Domain (per-image verified)",
            },
            "benchmark_overlap_defense": {
                "pre_download_check": "Active (BenchmarkLeakageIndex SHA-256 + source URL)",
                "post_download_sha256": "Active",
                "post_download_dhash_threshold": "Hamming distance <= 6 rejected",
                "intra_manifest_dedup": "Active",
            },
            "existing_source_ids_indexed": len(self.existing_source_ids),
            "existing_sha256s_indexed": len(self.existing_sha256s),
            "clean_splits_modified": False,
            "model_training": False,
            "weights_downloaded": False,
        }
        return plan

    def _acquire_boston_spec(
        self,
        spec: dict[str, Any],
        batch_manifest: dict[str, Any],
        intra_batch_source_ids: set[str],
        intra_batch_sha256s: set[str],
    ) -> None:
        canonical_cat = spec["category"]
        subtype = spec.get("subtype")
        query_type = spec["query_type"]
        target_count = spec["target_count"]
        source_name = spec["source_name"]
        batch_prefix = spec["batch_source_prefix"]

        images_dir = self.raw_dir / "boston311" / "batch_3" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        current_count = 0
        offset = spec["initial_offset"]

        print(
            f"\n[Boston 311] Acquiring up to {target_count} for "
            f"{canonical_cat} (subtype={subtype}, type='{query_type}')..."
        )

        while current_count < target_count:
            filters = json.dumps({"type": query_type})
            api_url = (
                "https://data.boston.gov/api/3/action/datastore_search?"
                f"resource_id={BOSTON_311_RESOURCE_2026}"
                f"&limit=100&offset={offset}"
                f"&filters={urllib.parse.quote(filters)}"
            )
            try:
                resp_bytes = fetch_url_with_retry(
                    api_url,
                    timeout=DEFAULT_TIMEOUT_SEC,
                    max_retries=self.max_retries,
                    delay_sec=self.delay_sec,
                )
                result = json.loads(resp_bytes.decode("utf-8")).get("result", {})
                records = result.get("records", [])
            except Exception as err:  # noqa: BLE001
                print(f"  Error querying CKAN at offset {offset}: {err}")
                batch_manifest["network_errors"] += 1
                break

            if not records:
                print(f"  No more records at offset {offset}. Source exhausted.")
                break

            offset += len(records)

            for rec in records:
                if current_count >= target_count:
                    break
                case_id = str(rec.get("case_enquiry_id") or rec.get("_id") or "")
                if not case_id:
                    continue
                if (
                    case_id in self.existing_source_ids
                    or case_id in intra_batch_source_ids
                ):
                    batch_manifest["duplicate_skips"] += 1
                    continue
                photo_url = rec.get("closed_photo") or rec.get("submittedphoto")
                if not photo_url or not photo_url.startswith("http"):
                    continue
                clean_url = photo_url.split("|")[0].split("#")[0].strip()
                sample_id = f"{batch_prefix}_{case_id}"

                pre_check = self.leakage_index.check_candidate(
                    sample_id=sample_id,
                    sha256="",
                    source_name=source_name,
                    source_record_id=case_id,
                    source_url=clean_url,
                )
                if not pre_check.passed:
                    batch_manifest["leakage_rejections"] += 1
                    batch_manifest["quarantined_candidates"].append({
                        "sample_id": sample_id,
                        "case_id": case_id,
                        "reason": f"Pre-download leakage: {pre_check.rejection_reason}",
                        "stage": "pre_download",
                    })
                    intra_batch_source_ids.add(case_id)
                    continue

                file_name = f"boston311_b3_{case_id}.jpg"
                img_dest = images_dir / file_name

                if not img_dest.exists():
                    try:
                        img_bytes = fetch_url_with_retry(
                            clean_url,
                            timeout=DEFAULT_TIMEOUT_SEC,
                            max_retries=self.max_retries,
                            delay_sec=self.delay_sec,
                        )
                        img_dest.write_bytes(img_bytes)
                    except Exception as err:  # noqa: BLE001
                        print(f"  Download failed {clean_url}: {err}")
                        batch_manifest["network_errors"] += 1
                        continue

                val_res = validate_image_file(img_dest)
                if not val_res.is_valid:
                    img_dest.unlink(missing_ok=True)
                    batch_manifest["validation_failures"] += 1
                    batch_manifest["quarantined_candidates"].append({
                        "sample_id": sample_id,
                        "case_id": case_id,
                        "reason": f"Validation failed: {val_res.rejection_reason}",
                        "stage": "post_download_validation",
                    })
                    intra_batch_source_ids.add(case_id)
                    continue

                if (
                    val_res.sha256 in intra_batch_sha256s
                    or val_res.sha256 in self.existing_sha256s
                ):
                    img_dest.unlink(missing_ok=True)
                    batch_manifest["duplicate_skips"] += 1
                    intra_batch_source_ids.add(case_id)
                    continue

                post_check = self.leakage_index.check_candidate(
                    sample_id=sample_id,
                    sha256=val_res.sha256,
                    source_name=source_name,
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
                        "reason": f"Post-download leakage: {post_check.rejection_reason}",
                        "stage": "post_download_leakage",
                        "min_dhash_distance": post_check.min_dhash_distance,
                    })
                    intra_batch_source_ids.add(case_id)
                    continue

                candidate_entry: dict[str, Any] = {
                    "sample_id": sample_id,
                    "batch_id": BATCH_ID,
                    "source_dataset": "boston311",
                    "source_name": source_name,
                    "source_record_id": case_id,
                    "canonical_category": canonical_cat,
                    "subtype": subtype,
                    "original_category": query_type,
                    "text_description": rec.get("type", query_type),
                    "image_rel_path": f"boston311/batch_3/images/{file_name}",
                    "license": spec["license"],
                    "license_url": spec["license_url"],
                    "attribution": spec["attribution"],
                    "source_url": clean_url,
                    "canonical_url": clean_url,
                    "acquisition_timestamp": datetime.now(UTC).isoformat(),
                    "acquisition_method": "ckan_api_controlled_download_batch3",
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
                        "group_id": f"grp_bost_b3_{case_id}",
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
                batch_manifest["candidates"].append(candidate_entry)
                batch_manifest["acquired_by_category"][canonical_cat] = (
                    batch_manifest["acquired_by_category"].get(canonical_cat, 0) + 1
                )
                intra_batch_source_ids.add(case_id)
                intra_batch_sha256s.add(val_res.sha256)
                current_count += 1
                total_acq = sum(batch_manifest["acquired_by_category"].values())
                if total_acq % 10 == 0:
                    print(f"  ... {total_acq} total candidates acquired in batch 3")

        print(
            f"  [Boston 311] {canonical_cat} '{query_type}': "
            f"acquired {current_count}/{target_count}"
        )

    def _acquire_wikimedia_spec(
        self,
        spec: dict[str, Any],
        batch_manifest: dict[str, Any],
        intra_batch_source_ids: set[str],
        intra_batch_sha256s: set[str],
    ) -> None:
        canonical_cat = spec["category"]
        subtype = spec.get("subtype")
        source_name = spec["source_name"]
        id_prefix = spec["id_prefix"]
        queries = spec["queries"]
        target_count = spec["target_count"]
        raw_subdir = spec["raw_subdir"]

        images_dir = self.raw_dir / raw_subdir / "batch_3" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        current_count = 0
        seen_pageids: set[str] = set(self.existing_source_ids)
        seen_pageids.update(intra_batch_source_ids)

        print(
            f"\n[Wikimedia] Acquiring up to {target_count} for {canonical_cat}..."
        )

        for query in queries:
            if current_count >= target_count:
                break

            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": 6,
                "gsrlimit": "50",
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
                "iiurlwidth": "1280",
                "format": "json",
            }
            api_url = WIKIMEDIA_API + "?" + urllib.parse.urlencode(params)

            try:
                api_resp = fetch_url_with_retry(
                    api_url,
                    timeout=DEFAULT_TIMEOUT_SEC,
                    max_retries=self.max_retries,
                    delay_sec=self.delay_sec,
                    headers={"User-Agent": WIKIMEDIA_USER_AGENT},
                )
                data = json.loads(api_resp.decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
            except Exception as err:  # noqa: BLE001
                print(f"  Wikimedia API failed for '{query}': {err}")
                batch_manifest["network_errors"] += 1
                continue

            for pageid_str, page in pages.items():
                if current_count >= target_count:
                    break
                if pageid_str in seen_pageids:
                    batch_manifest["duplicate_skips"] += 1
                    continue
                seen_pageids.add(pageid_str)

                ii_list = page.get("imageinfo", [])
                if not ii_list:
                    continue
                ii = ii_list[0]

                img_url = ii.get("thumburl") or ii.get("url", "")
                if not img_url or not img_url.startswith("http"):
                    continue

                size = ii.get("size", 0)
                if size > MAX_IMAGE_BYTES or size < 1000:
                    batch_manifest["quarantined_candidates"].append({
                        "sample_id": f"{id_prefix}_{pageid_str}",
                        "reason": f"Size out of bounds: {size}",
                        "stage": "pre_download_size_check",
                    })
                    continue

                extmeta = ii.get("extmetadata", {})
                lic = extmeta.get("LicenseShortName", {}).get("value", "Unknown")
                lic_url = extmeta.get("LicenseUrl", {}).get("value", "")
                artist_raw = extmeta.get("Artist", {}).get("value", "Unknown")
                desc_raw = extmeta.get("ImageDescription", {}).get("value", "")

                lic_upper = lic.upper()
                if not any(k in lic_upper for k in ACCEPTED_LICENSE_KEYWORDS):
                    batch_manifest["quarantined_candidates"].append({
                        "sample_id": f"{id_prefix}_{pageid_str}",
                        "reason": f"Unaccepted license: '{lic}'",
                        "stage": "pre_download_license_check",
                    })
                    continue

                artist = strip_html_tags(artist_raw) or "Wikimedia Contributor"
                desc = strip_html_tags(desc_raw)
                if len(desc) > 300:
                    desc = desc[:297] + "..."

                sample_id = f"{id_prefix}_{pageid_str}"

                pre_check = self.leakage_index.check_candidate(
                    sample_id=sample_id,
                    sha256="",
                    source_name=source_name,
                    source_record_id=pageid_str,
                    source_url=img_url,
                )
                if not pre_check.passed:
                    batch_manifest["leakage_rejections"] += 1
                    batch_manifest["quarantined_candidates"].append({
                        "sample_id": sample_id,
                        "pageid": pageid_str,
                        "reason": f"Pre-download leakage: {pre_check.rejection_reason}",
                        "stage": "pre_download",
                    })
                    continue

                file_name = f"{raw_subdir}_b3_{pageid_str}.jpg"
                img_dest = images_dir / file_name

                if not img_dest.exists():
                    try:
                        img_bytes = fetch_url_with_retry(
                            img_url,
                            timeout=DEFAULT_TIMEOUT_SEC,
                            max_retries=self.max_retries,
                            delay_sec=self.delay_sec,
                            headers={"User-Agent": WIKIMEDIA_USER_AGENT},
                        )
                        img_dest.write_bytes(img_bytes)
                    except Exception as err:  # noqa: BLE001
                        print(f"  Download failed pageid {pageid_str}: {err}")
                        batch_manifest["network_errors"] += 1
                        continue

                val_res = validate_image_file(img_dest)
                if not val_res.is_valid:
                    img_dest.unlink(missing_ok=True)
                    batch_manifest["validation_failures"] += 1
                    batch_manifest["quarantined_candidates"].append({
                        "sample_id": sample_id,
                        "pageid": pageid_str,
                        "reason": f"Validation failed: {val_res.rejection_reason}",
                        "stage": "post_download_validation",
                    })
                    continue

                if (
                    val_res.sha256 in intra_batch_sha256s
                    or val_res.sha256 in self.existing_sha256s
                ):
                    img_dest.unlink(missing_ok=True)
                    batch_manifest["duplicate_skips"] += 1
                    continue

                post_check = self.leakage_index.check_candidate(
                    sample_id=sample_id,
                    sha256=val_res.sha256,
                    source_name=source_name,
                    source_record_id=pageid_str,
                    source_url=img_url,
                    dhash=val_res.phash,
                )
                if not post_check.passed:
                    img_dest.unlink(missing_ok=True)
                    batch_manifest["leakage_rejections"] += 1
                    batch_manifest["quarantined_candidates"].append({
                        "sample_id": sample_id,
                        "pageid": pageid_str,
                        "reason": f"Post-download leakage: {post_check.rejection_reason}",
                        "stage": "post_download_leakage",
                        "min_dhash_distance": post_check.min_dhash_distance,
                    })
                    continue

                # Infer subtype for Other if from wikimedia
                inferred_subtype = subtype
                if canonical_cat == "Other":
                    q_lower = query.lower()
                    if "sign" in q_lower:
                        inferred_subtype = "damaged_road_sign"
                    elif "tree" in q_lower:
                        inferred_subtype = "fallen_tree_blockage"
                    elif "guardrail" in q_lower or "barrier" in q_lower:
                        inferred_subtype = "damaged_guardrail"
                    elif "bench" in q_lower:
                        inferred_subtype = "broken_bench"
                    else:
                        inferred_subtype = "other_documented_civic_defect"

                candidate_entry: dict[str, Any] = {
                    "sample_id": sample_id,
                    "batch_id": BATCH_ID,
                    "source_dataset": spec["source_dataset"],
                    "source_name": source_name,
                    "source_record_id": pageid_str,
                    "canonical_category": canonical_cat,
                    "subtype": inferred_subtype,
                    "original_category": query.strip('"'),
                    "text_description": (
                        desc
                        or f"{canonical_cat} infrastructure defect, public right-of-way"
                    ),
                    "image_rel_path": f"{raw_subdir}/batch_3/images/{file_name}",
                    "license": lic,
                    "license_url": lic_url or "https://creativecommons.org/",
                    "attribution": spec["attribution_template"].format(artist=artist),
                    "source_url": img_url,
                    "canonical_url": img_url,
                    "acquisition_timestamp": datetime.now(UTC).isoformat(),
                    "acquisition_method": "wikimedia_commons_api_batch3",
                    "original_metadata": {
                        "pageid": pageid_str,
                        "search_query": query,
                        "license": lic,
                        "artist": artist,
                    },
                    "grouping_metadata": {
                        "group_id": f"grp_{id_prefix}_{pageid_str}",
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
                batch_manifest["candidates"].append(candidate_entry)
                batch_manifest["acquired_by_category"][canonical_cat] = (
                    batch_manifest["acquired_by_category"].get(canonical_cat, 0) + 1
                )
                intra_batch_sha256s.add(val_res.sha256)
                current_count += 1
                total_acq = sum(batch_manifest["acquired_by_category"].values())
                if total_acq % 10 == 0:
                    print(f"  ... {total_acq} total candidates acquired in batch 3")

        print(
            f"  [Wikimedia] {canonical_cat}: acquired {current_count}/{target_count}"
        )

    def run_acquisition(self) -> dict[str, Any]:
        """Execute full Batch 3 acquisition."""
        if not self.execute:
            return self.run_dry_run()

        self.acquisition_dir.mkdir(parents=True, exist_ok=True)

        batch_manifest: dict[str, Any] = {
            "batch_id": BATCH_ID,
            "execution_timestamp": datetime.now(UTC).isoformat(),
            "batch_number": 3,
            "target_categories": [
                "Pothole",
                "Garbage",
                "Other",
                "Water Leakage",
                "Road Damage",
                "Streetlight",
            ],
            "target_summary": {
                "Pothole": BATCH_3_BOSTON_SPECS[0]["target_count"],
                "Garbage": BATCH_3_BOSTON_SPECS[1]["target_count"] + BATCH_3_BOSTON_SPECS[2]["target_count"],
                "Other": BATCH_3_BOSTON_SPECS[3]["target_count"] + BATCH_3_BOSTON_SPECS[4]["target_count"] + BATCH_3_WIKIMEDIA_SPECS[0]["target_count"],
                "Water Leakage": BATCH_3_WIKIMEDIA_SPECS[1]["target_count"],
                "Road Damage": BATCH_3_WIKIMEDIA_SPECS[2]["target_count"],
                "Streetlight": BATCH_3_WIKIMEDIA_SPECS[3]["target_count"],
            },
            "acquired_by_category": {},
            "duplicate_skips": 0,
            "leakage_rejections": 0,
            "validation_failures": 0,
            "network_errors": 0,
            "candidates": [],
            "quarantined_candidates": [],
        }

        intra_batch_source_ids: set[str] = set()
        intra_batch_sha256s: set[str] = set()

        # Wave 1: Boston 311 (Pothole, Garbage, Other)
        for spec in BATCH_3_BOSTON_SPECS:
            self._acquire_boston_spec(
                spec, batch_manifest, intra_batch_source_ids, intra_batch_sha256s
            )

        # Wave 2: Wikimedia Commons (Other subtypes, Water Leakage, Road Damage, Streetlight)
        for spec in BATCH_3_WIKIMEDIA_SPECS:
            self._acquire_wikimedia_spec(
                spec, batch_manifest, intra_batch_source_ids, intra_batch_sha256s
            )

        manifest_path = self.acquisition_dir / "batch_3_manifest.json"
        manifest_path.write_text(
            json.dumps(batch_manifest, indent=2), encoding="utf-8"
        )

        total = sum(batch_manifest["acquired_by_category"].values())
        print("\n" + "=" * 60)
        print(f"Batch 3 acquisition complete. Total candidates: {total}")
        print(f"By category: {batch_manifest['acquired_by_category']}")
        print(f"Leakage rejections: {batch_manifest['leakage_rejections']}")
        print(f"Duplicate skips: {batch_manifest['duplicate_skips']}")
        print(f"Validation failures: {batch_manifest['validation_failures']}")
        print(f"Network errors: {batch_manifest['network_errors']}")
        print(f"Manifest saved: {manifest_path}")
        print("=" * 60)
        return batch_manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CivicSense Phase 3.3 Step 6 Accelerated Controlled Acquisition Batch 3"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute real network download and staging (default: dry-run only)",
    )
    parser.add_argument(
        "--delay-sec",
        type=float,
        default=DEFAULT_DELAY_SEC,
        help=f"Per-request delay in seconds (default: {DEFAULT_DELAY_SEC})",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Max retry attempts (default: {DEFAULT_MAX_RETRIES})",
    )
    args = parser.parse_args()

    raw_dir = repo_root / "datasets" / "raw"
    benchmark_dir = repo_root / "datasets" / "benchmark_v1"
    training_dir = repo_root / "datasets" / "training_v1"

    runner = Batch3AcquisitionRunner(
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
        print("\nDRY-RUN only. Pass --execute to perform real acquisition.")
    else:
        runner.run_acquisition()


if __name__ == "__main__":
    main()
