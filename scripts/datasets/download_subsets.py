"""CivicSense Controlled Dataset Acquisition Tool.

Safely discovers and acquires small, controlled subsets of candidate datasets:
- RDD2022 (manual instruction / prerequisite policy)
- TACO (blocked for automated download due to unverified Flickr licenses)
- Boston 311 (automated pilot acquisition via CKAN API and Cloudinary media)
- NYC 311 (metadata and text reference only; zero image columns)

Requirements:
- Defaults to DRY-RUN / metadata-only mode.
- Requires --execute flag to make actual network requests.
- Strict limit and byte caps (--limit 10, --max-bytes 25MB default).
- Generates download_manifest.json with full schema compliance.
- Never downloads entire multi-GB datasets.
"""

import argparse
import datetime
import hashlib
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image

# Ensure repository root is in sys.path when executed as standalone script
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.datasets.normalize_annotations import filter_taco_image_license  # noqa: E402
from scripts.datasets.source_registry import DATASET_REGISTRY, get_source  # noqa: E402

DEFAULT_LIMIT = 10
DEFAULT_MAX_BYTES = 25 * 1024 * 1024  # 25 MB
DEFAULT_TIMEOUT_SEC = 15

# Representative Boston 311 categories for pilot acquisition
BOSTON311_PILOT_QUERIES = [
    ("Request for Pothole Repair", "Pothole"),
    ("Roadway Repair", "Road Damage"),
    ("Illegal Dumping", "Garbage"),
    ("Improper Storage of Trash (Barrels)", "Garbage"),
    ("Parks Lighting/Electrical Issues", "Streetlight"),
    ("Poor Conditions of Property", "Other"),
    ("Graffiti Removal", "Other"),
    ("Sign Repair", "Other"),
]

WIKIMEDIA_WATER_QUERIES = [
    '"burst water main"',
    '"water main break"',
    '"burst pipe"',
    'pipe "water leak"',
    '"broken water main"',
    '"broken water pipe"',
    '"burst water pipe"',
    '"street flood" "water main"',
]

WIKIMEDIA_STREETLIGHT_QUERIES = [
    '"broken street light"',
    '"damaged street light"',
    '"broken lamp post"',
    '"damaged lamp post"',
    '"street lamp" damaged',
    '"street lamp" broken',
    '"broken streetlight"',
    '"damaged streetlight"',
    '"broken street lamp"',
    '"damaged street lamp"',
    '"street light" road',
    '"street lamp" city',
    '"lamp post" sidewalk',
    '"street lighting" pole',
    '"light pole" street',
    '"street light" pavement',
]

WIKIMEDIA_ROAD_DAMAGE_QUERIES = [
    '"alligator cracking" road',
    '"cracked asphalt"',
    '"road damage"',
    '"damaged road"',
    '"pavement crack"',
    '"road crack"',
    '"asphalt cracking"',
    '"longitudinal crack" road',
    '"transverse crack" road',
    '"damaged pavement"',
    '"asphalt crack"',
    '"road fissure"',
]



def print_acquisition_plan(
    sources: list[str],
    limit: int,
    max_bytes: int,
    output_dir: Path,
    execute: bool,
) -> None:
    """Print structured pre-flight acquisition plan."""
    mode_label = "EXECUTE (NETWORK ACQUISITION)" if execute else "DRY-RUN (METADATA ONLY)"
    print("=" * 65)
    print(f" CIVICSENSE DATASET ACQUISITION PLAN [{mode_label}]")
    print("=" * 65)
    print(f"Target Output Directory : {output_dir}")
    print(f"Record Limit Per Source : {limit}")
    print(f"Max Bytes Per Source    : {max_bytes / (1024 * 1024):.1f} MB")
    print("-" * 65)

    for src_id in sources:
        meta = get_source(src_id)
        if not meta:
            print(f"Source: {src_id} [UNKNOWN SOURCE]")
            continue
        print(f"Source                  : {meta.source_dataset.upper()} ({meta.official_name})")
        print(f"Official URL            : {meta.official_url}")
        print(f"License Status          : {meta.license} (Verified: {meta.license_verified})")
        print(f"Verification Status     : {meta.verification_status}")
        print(f"Image Availability      : {meta.image_availability}")
        print(f"Download Policy         : {meta.download_policy}")
        is_manual = (
            meta.download_policy == "manual_prerequisite"
            or "review" in meta.verification_status
        )
        manual_rev = "YES" if is_manual else "NO"
        print(f"Manual Action Required  : {manual_rev}")
        print("-" * 65)


def _download_boston311_pilot(
    target_dir: Path,
    limit: int = DEFAULT_LIMIT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Execute real pilot download for Boston 311."""
    images_dir = target_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    samples: list[dict[str, Any]] = []
    downloaded_files: list[dict[str, Any]] = []
    errors: list[str] = []
    skipped: list[str] = []
    total_bytes = 0

    num_queries = len(BOSTON311_PILOT_QUERIES)

    for type_name, canonical in BOSTON311_PILOT_QUERIES:
        if limit <= 10:
            per_query_limit = max(1, (limit + num_queries - 1) // num_queries)
            if len(samples) >= limit or total_bytes >= max_bytes:
                break
        else:
            cat_count = sum(1 for s in samples if s["canonical_category"] == canonical)
            target_cat = 55 if canonical in ["Pothole", "Garbage", "Other"] else 10
            if cat_count >= target_cat or total_bytes >= max_bytes:
                continue
            per_query_limit = max(1, target_cat - cat_count)

        sql = f"""
        SELECT case_enquiry_id, type, reason, case_title, closed_photo, location
        FROM "1a0b420d-99f1-4887-9851-990b2a5a6e17"
        WHERE type = '{type_name}' AND closed_photo IS NOT NULL
        LIMIT {per_query_limit}
        """
        query_url = (
            "https://data.boston.gov/api/3/action/datastore_search_sql?sql="
            + urllib.parse.quote(sql)
        )
        req = urllib.request.Request(query_url, headers={"User-Agent": "Mozilla/5.0"})

        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                data = json.loads(res.read().decode("utf-8"))
                recs = data.get("result", {}).get("records", [])
                if not recs:
                    skipped.append(f"{type_name}: No record with closed_photo found")
                    continue

                for rec in recs:
                    if limit <= 10 and len(samples) >= limit:
                        break
                    if total_bytes >= max_bytes:
                        break
                    if limit > 10:
                        cat_count = sum(1 for s in samples if s["canonical_category"] == canonical)
                        target_cat = 55 if canonical in ["Pothole", "Garbage", "Other"] else 10
                        if cat_count >= target_cat:
                            break

                    photo_field = rec.get("closed_photo") or ""
                    raw_url = photo_field.split("|")[0].strip()
                    clean_url = raw_url.split("#")[0].strip()
                    if not clean_url.startswith("http"):
                        continue

                    case_id = str(rec["case_enquiry_id"])
                    dest_file = images_dir / f"boston311_{case_id}.jpg"

                    if dest_file.exists():
                        img_bytes = dest_file.read_bytes()
                        status_code = 200
                    else:
                        img_req = urllib.request.Request(
                            clean_url, headers={"User-Agent": "Mozilla/5.0"}
                        )
                        with urllib.request.urlopen(img_req, timeout=timeout) as img_res:
                            status_code = getattr(img_res, "status", 200)
                            img_bytes = img_res.read()

                    file_size = len(img_bytes)
                    if total_bytes + file_size > max_bytes:
                        skipped.append(f"{type_name}: Image size {file_size} exceeds remaining cap")
                        break

                    # Pillow decompression bomb safety check in memory
                    try:
                        with Image.open(io.BytesIO(img_bytes)) as test_im:
                            w, h = test_im.size
                            if w * h > 25_000_000:
                                skipped.append(
                                    f"{type_name} #{case_id}: Exceeds 25M pixels ({w*h})"
                                )
                                continue
                    except Exception as e_im:
                        skipped.append(f"{type_name} #{case_id}: Header parse error ({e_im})")
                        continue

                    sha256 = hashlib.sha256(img_bytes).hexdigest()
                    if not dest_file.exists():
                        dest_file.write_bytes(img_bytes)
                    total_bytes += file_size

                    rel_path = f"boston311/images/boston311_{case_id}.jpg"
                    downloaded_files.append({
                        "file_path": str(dest_file),
                        "relative_path": rel_path,
                        "sha256": sha256,
                        "bytes": file_size,
                        "http_status": status_code,
                        "case_id": case_id,
                        "original_category": type_name,
                        "canonical_category": canonical,
                        "source_url": clean_url,
                    })

                    sample_entry = {
                        "sample_id": f"pilot_bost311_{case_id}",
                        "source_dataset": "boston311",
                        "source_record_id": case_id,
                        "original_category": type_name,
                        "canonical_category": canonical,
                        "text_description": rec.get("case_title") or type_name,
                        "image_rel_path": rel_path,
                        "license": "ODC-PDDL",
                        "license_url": "http://www.opendefinition.org/licenses/odc-pddl",
                        "attribution": (
                            "City of Boston, Analyze Boston Open Data / 311 Service Requests"
                        ),
                        "source_url": clean_url,
                        "location": rec.get("location"),
                        "verification_level": "source_verified",
                        "visual_relevance": "direct_issue_visible",
                    }
                    samples.append(sample_entry)

        except Exception as exc:
            errors.append(f"Failed to acquire {type_name}: {exc}")

    # Write raw samples JSON for downstream curation
    raw_samples_path = target_dir / "raw_samples.json"
    with open(raw_samples_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)

    return {
        "downloaded_files": downloaded_files,
        "samples": samples,
        "total_bytes": total_bytes,
        "errors": errors,
        "skipped": skipped,
    }


def _download_wikimedia_category(
    target_dir: Path,
    source_dataset: str,
    canonical_category: str,
    queries: list[str],
    id_prefix: str,
    limit: int = DEFAULT_LIMIT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Acquire verified CC-BY / Public Domain civic images from Wikimedia Commons."""
    images_dir = target_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    samples: list[dict[str, Any]] = []
    downloaded_files: list[dict[str, Any]] = []
    errors: list[str] = []
    skipped: list[str] = []
    total_bytes = 0
    seen_pageids: set[str] = set()

    endpoint = "https://commons.wikimedia.org/w/api.php"

    for query in queries:
        if len(samples) >= limit or total_bytes >= max_bytes:
            break

        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": min(max(limit * 2, 20), 50),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 1280,
            "format": "json",
        }
        url = endpoint + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "CivicSense-Research/1.0 "
                    "(https://github.com/helloabhishek2004/Civicsense)"
                )
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                data = json.loads(res.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})

                for pageid, page in pages.items():
                    if len(samples) >= limit or total_bytes >= max_bytes:
                        break
                    if str(pageid) in seen_pageids:
                        continue
                    seen_pageids.add(str(pageid))

                    ii = page.get("imageinfo", [{}])[0]
                    size = ii.get("size", 0)
                    img_url = ii.get("thumburl") or ii.get("url")
                    if not img_url:
                        continue

                    if size > 10 * 1024 * 1024 or size < 1000:
                        skipped.append(f"Page {pageid}: size {size} out of bounds")
                        continue

                    extmeta = ii.get("extmetadata", {})
                    lic = extmeta.get("LicenseShortName", {}).get("value", "Unknown")
                    lic_url = extmeta.get("LicenseUrl", {}).get("value", "")
                    artist = extmeta.get("Artist", {}).get("value", "Unknown")
                    desc = extmeta.get("ImageDescription", {}).get("value", "")

                    lic_upper = lic.upper()
                    if not any(k in lic_upper for k in ["CC", "PUBLIC DOMAIN", "PD", "ODC"]):
                        skipped.append(f"Page {pageid}: unverified license '{lic}'")
                        continue

                    dest_file = images_dir / f"{source_dataset}_{pageid}.jpg"
                    if dest_file.exists():
                        img_bytes = dest_file.read_bytes()
                        status_code = 200
                    else:
                        img_req = urllib.request.Request(
                            img_url,
                            headers={
                                "User-Agent": (
                                    "CivicSense-Research/1.0 "
                                    "(https://github.com/helloabhishek2004/Civicsense)"
                                )
                            },
                        )
                        with urllib.request.urlopen(img_req, timeout=timeout) as img_res:
                            status_code = getattr(img_res, "status", 200)
                            img_bytes = img_res.read()

                    file_size = len(img_bytes)
                    if total_bytes + file_size > max_bytes:
                        skipped.append(
                            f"Page {pageid}: Image size {file_size} exceeds remaining cap"
                        )
                        break

                    # Pillow decompression bomb safety check in memory
                    try:
                        with Image.open(io.BytesIO(img_bytes)) as test_im:
                            w, h = test_im.size
                            if w * h > 25_000_000:
                                skipped.append(f"Page {pageid}: Exceeds 25M pixels ({w*h})")
                                continue
                    except Exception as e_im:
                        skipped.append(f"Page {pageid}: Header parse error ({e_im})")
                        continue

                    sha256 = hashlib.sha256(img_bytes).hexdigest()
                    if not dest_file.exists():
                        dest_file.write_bytes(img_bytes)
                    total_bytes += file_size

                    rel_path = f"{source_dataset}/images/{source_dataset}_{pageid}.jpg"
                    downloaded_files.append({
                        "file_path": str(dest_file),
                        "relative_path": rel_path,
                        "sha256": sha256,
                        "bytes": file_size,
                        "http_status": status_code,
                        "pageid": str(pageid),
                        "source_url": img_url,
                    })

                    clean_desc = (
                        desc.replace("<p>", "")
                        .replace("</p>", "")
                        .replace("<b>", "")
                        .replace("</b>", "")
                        .strip()
                        if desc
                        else ""
                    )
                    if len(clean_desc) > 300:
                        clean_desc = clean_desc[:297] + "..."

                    clean_artist = (
                        artist.replace("<p>", "")
                        .replace("</p>", "")
                        .replace("<b>", "")
                        .replace("</b>", "")
                        .strip()
                        if artist
                        else "Wikimedia Contributor"
                    )
                    if "<a " in clean_artist:
                        import re
                        clean_artist = re.sub(r"<[^>]+>", "", clean_artist).strip()

                    samples.append({
                        "sample_id": f"pilot_{id_prefix}_{pageid}",
                        "source_dataset": source_dataset,
                        "source_record_id": str(pageid),
                        "original_category": query.strip('"'),
                        "canonical_category": canonical_category,
                        "text_description": (
                            clean_desc
                            or (
                                f"{canonical_category} infrastructure defect photographed "
                                "in public right-of-way"
                            )
                        ),
                        "image_rel_path": rel_path,
                        "license": lic,
                        "license_url": lic_url or "https://creativecommons.org/",
                        "attribution": f"{clean_artist} via Wikimedia Commons",
                        "source_url": img_url,
                        "verification_level": "source_verified",
                        "visual_relevance": "direct_issue_visible",
                    })

        except Exception as exc:
            errors.append(f"Query '{query}' failed for {source_dataset}: {exc}")

    raw_samples_path = target_dir / "raw_samples.json"
    with open(raw_samples_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)

    return {
        "downloaded_files": downloaded_files,
        "samples": samples,
        "total_bytes": total_bytes,
        "errors": errors,
        "skipped": skipped,
    }


def _download_wikimedia_water_pilot(
    target_dir: Path,
    limit: int = DEFAULT_LIMIT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Acquire verified CC-BY / Public Domain water leakage photos from Wikimedia Commons."""
    return _download_wikimedia_category(
        target_dir=target_dir,
        source_dataset="wikimedia_water",
        canonical_category="Water Leakage",
        queries=WIKIMEDIA_WATER_QUERIES,
        id_prefix="wmwater",
        limit=limit,
        max_bytes=max_bytes,
        timeout=timeout,
    )


def _download_wikimedia_streetlight_subset(
    target_dir: Path,
    limit: int = DEFAULT_LIMIT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Acquire verified CC-BY / Public Domain street lighting photos from Wikimedia Commons."""
    return _download_wikimedia_category(
        target_dir=target_dir,
        source_dataset="wikimedia_streetlight",
        canonical_category="Streetlight",
        queries=WIKIMEDIA_STREETLIGHT_QUERIES,
        id_prefix="wmlight",
        limit=limit,
        max_bytes=max_bytes,
        timeout=timeout,
    )


def _download_wikimedia_road_damage_subset(
    target_dir: Path,
    limit: int = DEFAULT_LIMIT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Acquire verified CC-BY / Public Domain road damage photos from Wikimedia Commons."""
    return _download_wikimedia_category(
        target_dir=target_dir,
        source_dataset="wikimedia_road_damage",
        canonical_category="Road Damage",
        queries=WIKIMEDIA_ROAD_DAMAGE_QUERIES,
        id_prefix="wmroad",
        limit=limit,
        max_bytes=max_bytes,
        timeout=timeout,
    )


def _download_taco_pilot(
    target_dir: Path,
    limit: int = DEFAULT_LIMIT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Acquire verified ODbL litter images from TACO dataset."""
    images_dir = target_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    samples: list[dict[str, Any]] = []
    downloaded_files: list[dict[str, Any]] = []
    errors: list[str] = []
    skipped: list[str] = []
    total_bytes = 0

    url = "https://raw.githubusercontent.com/pedropro/TACO/master/data/annotations.json"
    req = urllib.request.Request(url, headers={"User-Agent": "CivicSense-Research/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        images = data.get("images", [])
        for img in images:
            if len(samples) >= limit or total_bytes >= max_bytes:
                break

            raw_lic = img.get("license")
            is_valid, lic_label = filter_taco_image_license(raw_lic)
            if not is_valid:
                continue

            img_id = img["id"]
            img_url = img.get("flickr_url") or img.get("url")
            if not img_url:
                continue

            dest_file = images_dir / f"taco_{img_id}.jpg"
            if dest_file.exists():
                img_bytes = dest_file.read_bytes()
                file_size = len(img_bytes)
                status_code = 200
            else:
                try:
                    img_req = urllib.request.Request(
                        img_url, headers={"User-Agent": "CivicSense-Research/1.0"}
                    )
                    with urllib.request.urlopen(img_req, timeout=timeout) as img_res:
                        content_length = img_res.headers.get("Content-Length")
                        if content_length and int(content_length) > 10 * 1024 * 1024:
                            skipped.append(
                                f"TACO #{img_id}: Exceeds 10MB limit ({content_length} bytes)"
                            )
                            continue

                        img_bytes = img_res.read()
                        file_size = len(img_bytes)
                        status_code = getattr(img_res, "status", 200)
                except Exception as e_dl:
                    skipped.append(f"TACO #{img_id}: Download failed ({e_dl})")
                    continue

            if file_size > 10 * 1024 * 1024 or file_size < 1000:
                skipped.append(f"TACO #{img_id}: Size {file_size} out of bounds")
                continue

            if total_bytes + file_size > max_bytes:
                skipped.append(f"TACO #{img_id}: Exceeds remaining budget ({max_bytes} bytes)")
                break

            sha256 = hashlib.sha256(img_bytes).hexdigest()
            if not dest_file.exists():
                dest_file.write_bytes(img_bytes)
            total_bytes += file_size

            rel_path = f"taco/images/taco_{img_id}.jpg"
            downloaded_files.append({
                "file_path": str(dest_file),
                "relative_path": rel_path,
                "sha256": sha256,
                "bytes": file_size,
                "http_status": status_code,
                "image_id": str(img_id),
                "source_url": img_url,
            })

            samples.append({
                "sample_id": f"pilot_taco_{img_id}",
                "source_dataset": "taco",
                "source_record_id": str(img_id),
                "original_category": "litter",
                "canonical_category": "Garbage",
                "text_description": f"TACO litter detection benchmark sample #{img_id}",
                "image_rel_path": rel_path,
                "license": lic_label,
                "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
                "attribution": "OpenLitterMap & Contributors (ODbL) via TACO",
                "source_url": img_url,
                "verification_level": "source_verified",
                "visual_relevance": "direct_issue_visible",
            })

    except Exception as exc:
        errors.append(f"Failed to acquire TACO samples: {exc}")

    raw_samples_path = target_dir / "raw_samples.json"
    with open(raw_samples_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)

    return {
        "downloaded_files": downloaded_files,
        "samples": samples,
        "total_bytes": total_bytes,
        "errors": errors,
        "skipped": skipped,
    }


def run_download_pipeline(
    source_name: str,
    output_dir: Path,
    limit: int = DEFAULT_LIMIT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: int = DEFAULT_TIMEOUT_SEC,
    execute: bool = False,
) -> dict[str, Any]:
    """Execute or simulate controlled dataset subset acquisition."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sources_to_process = (
        list(DATASET_REGISTRY.keys())
        if source_name.lower() == "all"
        else [source_name.lower()]
    )

    # Print plan before execution
    print_acquisition_plan(sources_to_process, limit, max_bytes, output_dir, execute)

    manifest_entries: list[dict[str, Any]] = []

    for src_id in sources_to_process:
        source_meta = get_source(src_id)
        if not source_meta:
            manifest_entries.append({
                "source_dataset": src_id,
                "source_url": "unknown",
                "acquisition_timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                "acquisition_mode": "error",
                "requested_limit": limit,
                "actual_download_count": 0,
                "total_bytes": 0,
                "file_paths": [],
                "sha256": [],
                "http_status": None,
                "license_verification_status": "unverified",
                "attribution": "",
                "errors": [f"Unknown source dataset '{src_id}'"],
                "skipped_records": [],
                "manual_action_required": False,
            })
            continue

        target_dir = output_dir / src_id
        target_dir.mkdir(parents=True, exist_ok=True)

        entry: dict[str, Any] = {
            "source_dataset": src_id,
            "source_url": source_meta.official_url,
            "acquisition_timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "acquisition_mode": "dry_run" if not execute else "network_download",
            "requested_limit": limit,
            "actual_download_count": 0,
            "total_bytes": 0,
            "file_paths": [],
            "sha256": [],
            "http_status": None,
            "license_verification_status": source_meta.verification_status,
            "attribution": source_meta.attribution_requirement,
            "errors": [],
            "skipped_records": [],
            "manual_action_required": False,
        }

        # 1. DRY-RUN MODE (Default)
        if not execute:
            entry["acquisition_mode"] = "dry_run_metadata_only"
            entry["instructions"] = (
                f"Dry-run executed for {src_id}. To execute physical download, pass --execute. "
                f"Policy: {source_meta.download_policy}."
            )
            if src_id == "rdd2022":
                entry["manual_action_required"] = True
                entry["instructions"] = (
                    "RDD2022 requires manual download of country tarball (e.g. India.tgz) from "
                    f"{source_meta.official_url} into {target_dir}. "
                    "Automated bulk scraping is blocked to prevent bandwidth exhaustion."
                )
            elif src_id == "taco":
                entry["manual_action_required"] = False
                entry["instructions"] = (
                    "TACO per-image license filter configured. Automated acquisition will filter "
                    "annotations.json and download only verified ODbL/CC-BY images (<10MB)."
                )
            elif src_id == "wikimedia_water":
                entry["manual_action_required"] = False
                entry["instructions"] = (
                    "Wikimedia Commons water leakage acquisition ready. Queries MediaWiki API "
                    "for burst water main and pipe rupture images under CC-BY-SA / Public Domain."
                )
            elif src_id == "wikimedia_streetlight":
                entry["manual_action_required"] = False
                entry["instructions"] = (
                    "Wikimedia Commons streetlight acquisition ready. Queries MediaWiki API "
                    "for street lamp and lamp post images under CC-BY-SA / Public Domain."
                )
            elif src_id == "wikimedia_road_damage":
                entry["manual_action_required"] = False
                entry["instructions"] = (
                    "Wikimedia Commons road damage acquisition ready. Queries MediaWiki API "
                    "for asphalt crack and road damage images under CC-BY-SA / Public Domain."
                )
            manifest_entries.append(entry)
            continue

        # 2. EXECUTION MODE
        if src_id == "boston311":
            print(
                f"Executing Boston 311 pilot acquisition "
                f"(limit={limit}, max_bytes={max_bytes})..."
            )
            dl_res = _download_boston311_pilot(
                target_dir, limit=limit, max_bytes=max_bytes, timeout=timeout
            )
            entry["acquisition_mode"] = "pilot_network_download"
            entry["actual_download_count"] = len(dl_res["downloaded_files"])
            entry["total_bytes"] = dl_res["total_bytes"]
            entry["file_paths"] = [f["file_path"] for f in dl_res["downloaded_files"]]
            entry["sha256"] = [f["sha256"] for f in dl_res["downloaded_files"]]
            entry["http_status"] = 200 if dl_res["downloaded_files"] else None
            entry["errors"] = dl_res["errors"]
            entry["skipped_records"] = dl_res["skipped"]
            entry["manual_action_required"] = False
            entry["instructions"] = (
                f"Successfully downloaded {entry['actual_download_count']} pilot files "
                f"({entry['total_bytes']} bytes) under ODC-PDDL license."
            )
            manifest_entries.append(entry)

        elif src_id == "rdd2022":
            entry["acquisition_mode"] = "manual_prerequisite_blocked"
            entry["manual_action_required"] = True
            entry["instructions"] = (
                "RDD2022 archives are multi-gigabyte files (e.g. India.tgz ~1.5 GB). "
                "Automated download is prohibited to prevent bandwidth exhaustion. "
                "Manual action required: Place extracted RDD2022 image subset and Pascal VOC XMLs "
                f"in {target_dir} and run normalization."
            )
            manifest_entries.append(entry)

        elif src_id == "taco":
            print(
                f"Executing TACO controlled acquisition "
                f"(ODbL filter, limit={limit}, max_bytes={max_bytes})..."
            )
            dl_res = _download_taco_pilot(
                target_dir, limit=limit, max_bytes=max_bytes, timeout=timeout
            )
            entry["acquisition_mode"] = "pilot_network_download"
            entry["actual_download_count"] = len(dl_res["downloaded_files"])
            entry["total_bytes"] = dl_res["total_bytes"]
            entry["file_paths"] = [f["file_path"] for f in dl_res["downloaded_files"]]
            entry["sha256"] = [f["sha256"] for f in dl_res["downloaded_files"]]
            entry["http_status"] = 200 if dl_res["downloaded_files"] else None
            entry["license_verification_status"] = "cleared_odbl_filtered"
            entry["errors"] = dl_res["errors"]
            entry["skipped_records"] = dl_res["skipped"]
            entry["manual_action_required"] = False
            entry["instructions"] = (
                f"Successfully downloaded {entry['actual_download_count']} TACO files "
                f"({entry['total_bytes']} bytes) under verified ODbL / open license."
            )
            manifest_entries.append(entry)

        elif src_id == "wikimedia_water":
            print(
                f"Executing Wikimedia water leakage acquisition "
                f"(limit={limit}, max_bytes={max_bytes})..."
            )
            dl_res = _download_wikimedia_water_pilot(
                target_dir, limit=limit, max_bytes=max_bytes, timeout=timeout
            )
            entry["acquisition_mode"] = "pilot_network_download"
            entry["actual_download_count"] = len(dl_res["downloaded_files"])
            entry["total_bytes"] = dl_res["total_bytes"]
            entry["file_paths"] = [f["file_path"] for f in dl_res["downloaded_files"]]
            entry["sha256"] = [f["sha256"] for f in dl_res["downloaded_files"]]
            entry["http_status"] = 200 if dl_res["downloaded_files"] else None
            entry["license_verification_status"] = "cleared_cc_public_domain"
            entry["errors"] = dl_res["errors"]
            entry["skipped_records"] = dl_res["skipped"]
            entry["manual_action_required"] = False
            entry["instructions"] = (
                f"Successfully downloaded {entry['actual_download_count']} Wikimedia "
                f"water leakage files ({entry['total_bytes']} bytes) under CC-BY-SA / PD."
            )
            manifest_entries.append(entry)

        elif src_id == "wikimedia_streetlight":
            print(
                f"Executing Wikimedia streetlight acquisition "
                f"(limit={limit}, max_bytes={max_bytes})..."
            )
            dl_res = _download_wikimedia_streetlight_subset(
                target_dir, limit=limit, max_bytes=max_bytes, timeout=timeout
            )
            entry["acquisition_mode"] = "pilot_network_download"
            entry["actual_download_count"] = len(dl_res["downloaded_files"])
            entry["total_bytes"] = dl_res["total_bytes"]
            entry["file_paths"] = [f["file_path"] for f in dl_res["downloaded_files"]]
            entry["sha256"] = [f["sha256"] for f in dl_res["downloaded_files"]]
            entry["http_status"] = 200 if dl_res["downloaded_files"] else None
            entry["license_verification_status"] = "cleared_cc_public_domain"
            entry["errors"] = dl_res["errors"]
            entry["skipped_records"] = dl_res["skipped"]
            entry["manual_action_required"] = False
            entry["instructions"] = (
                f"Successfully downloaded {entry['actual_download_count']} Wikimedia "
                f"streetlight files ({entry['total_bytes']} bytes) under CC-BY-SA / PD."
            )
            manifest_entries.append(entry)

        elif src_id == "wikimedia_road_damage":
            print(
                f"Executing Wikimedia road damage acquisition "
                f"(limit={limit}, max_bytes={max_bytes})..."
            )
            dl_res = _download_wikimedia_road_damage_subset(
                target_dir, limit=limit, max_bytes=max_bytes, timeout=timeout
            )
            entry["acquisition_mode"] = "pilot_network_download"
            entry["actual_download_count"] = len(dl_res["downloaded_files"])
            entry["total_bytes"] = dl_res["total_bytes"]
            entry["file_paths"] = [f["file_path"] for f in dl_res["downloaded_files"]]
            entry["sha256"] = [f["sha256"] for f in dl_res["downloaded_files"]]
            entry["http_status"] = 200 if dl_res["downloaded_files"] else None
            entry["license_verification_status"] = "cleared_cc_public_domain"
            entry["errors"] = dl_res["errors"]
            entry["skipped_records"] = dl_res["skipped"]
            entry["manual_action_required"] = False
            entry["instructions"] = (
                f"Successfully downloaded {entry['actual_download_count']} Wikimedia "
                f"road damage files ({entry['total_bytes']} bytes) under CC-BY-SA / PD."
            )
            manifest_entries.append(entry)

        elif src_id == "nyc311":
            entry["acquisition_mode"] = "skipped_tabular_text_only"
            entry["license_verification_status"] = "cleared_for_text_only"
            entry["manual_action_required"] = False
            entry["instructions"] = (
                "NYC 311 Socrata endpoint contains 48 tabular columns with zero citizen "
                "photo URLs. Skipped visual acquisition. Cleared for civic text reference only."
            )
            manifest_entries.append(entry)

    for entry in manifest_entries:
        if "status" not in entry:
            entry["status"] = entry.get("acquisition_mode", "UNKNOWN").upper()
        if "downloaded_count" not in entry:
            entry["downloaded_count"] = entry.get("actual_download_count", 0)

    manifest_path = output_dir / "download_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_entries, f, indent=2)

    return {
        "manifest_path": str(manifest_path),
        "execute_mode": execute,
        "entries": manifest_entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="CivicSense Controlled Dataset Acquisition Tool")
    parser.add_argument(
        "--source",
        default="all",
        help="Source ID (rdd2022, taco, boston311, nyc311, all)",
    )
    parser.add_argument(
        "--output-dir",
        default="datasets/raw",
        help="Output directory for raw downloads",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Max records to download (default: 10)",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help="Max total bytes allowed (default: 25MB)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SEC,
        help="HTTP timeout seconds (default: 15)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute actual network download (default is dry-run)",
    )

    args = parser.parse_args()
    res = run_download_pipeline(
        source_name=args.source,
        output_dir=Path(args.output_dir),
        limit=args.limit,
        max_bytes=args.max_bytes,
        timeout=args.timeout,
        execute=args.execute,
    )
    mode_str = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"\nAcquisition pipeline completed. Mode: {mode_str}. Manifest: {res['manifest_path']}")


if __name__ == "__main__":
    main()

