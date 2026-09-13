# CivicSense — Phase 3.2 Step 4A Implementation Report
## Controlled Dataset Acquisition, Validation, and Pilot Benchmark Assembly

**Execution Date:** 2026-09-13  
**Status:** Complete  
**Governance:** AGENTS.md | memory.md  
**Scope:** Phase 3.2 Step 4A (Pilot Acquisition, Ingestion Validation, Deduplication, Manual Review Cataloging, and Preliminary Pilot Benchmark Assembly)

---

## 1. Executive Summary

In accordance with CivicSense AI/ML engineering standards, **Phase 3.2 Step 4A** executed controlled pilot acquisition, rigorous forensic licensing verification, defensive image validation, perceptual deduplication, and assembly of a **preliminary pilot dataset**.

Crucially, in adherence to Rule 0, Rule 6, and AGENTS.md:
- **No neural model training or inference was executed.**
- **No heavy ML dependencies were introduced** (strict standard library + Pillow footprint preserved).
- **No production database, API routes, or AI pipeline logic were modified.**
- **Zero synthetic padding or artificial inflation was applied**; real-world category shortages are honestly preserved.
- **The dataset is explicitly classified as a *Preliminary Pilot Dataset*, NOT *benchmark_v1 ready*.**
- **Baseline evaluation is NOT eligible to proceed yet**, pending resolution of specific source clearances and sample shortages documented herein.

---

## 2. Forensic Source & Licensing Verification

All 4 candidate sources identified in Phase 3.1 were audited against live official endpoints, licenses, schemas, and media availability:

| Source | Target Categories | Verified License | Hosting Architecture & Media Availability | Benchmark Clearance Status |
| :--- | :--- | :--- | :--- | :--- |
| **Boston 311** | Pothole, Road Damage, Garbage, Streetlight, Other | **ODC-PDDL** (Public Domain Dedication) | Live Cloudinary URLs (`spot-boston-res.cloudinary.com`) via CKAN datastore | **CLEARED FOR VISUAL PILOT** |
| **TACO** | Garbage | **CC BY-SA 4.0** (Annotations) / **47.7% Unverified Flickr** | Flickr CDN via COCO `annotations.json` | **NOT CLEARED FOR AUTOMATED INGESTION** (Flagged for manual review) |
| **RDD2022** | Pothole, Road Damage | **CC BY-NC 3.0** (Mendeley Data DOI: 10.17632/5ty2wb6gvg.1) | Multi-GB tarballs (`India.tgz` ~1.5 GB) on Mendeley Data | **MANUAL PREREQUISITE REQUIRED** (Automated scraping blocked) |
| **NYC 311** | Text Reference Only | **NYC Open Data Terms of Use** (Public Domain) | Socrata API (`erm2-nwe9`): 48 tabular columns, **0 media columns** | **NOT CLEARED FOR VISUAL BENCHMARK** (Text-only reference) |

### Key Forensic Findings

1. **TACO Licensing Ambiguity (Critical Discovery)**:
   - Deep inspection of official `annotations.json` reveals that **715 out of 1,500 images (47.7%) have `license: null`**.
   - An additional 319 records carry an ambiguous string `'CC'` without indicating the specific Creative Commons version.
   - Only 466 images specify distinct CC licenses (e.g., CC BY-NC-SA 2.0, CC BY 2.0).
   - **Action Taken:** Automated bulk downloading was blocked by policy in `scripts/datasets/download_subsets.py`. Flagged in `datasets/raw/manual_review.json`. A per-image license filter must be implemented before any TACO images enter the benchmark.

2. **RDD2022 Bandwidth & Packaging Constraint**:
   - The authoritative dataset is distributed via Mendeley Data as large national tarballs (`India.tgz` ~1.5 GB, `Japan.tgz`, `Czech.tgz`).
   - Automated HTTP scraping against Mendeley endpoints risks rate limits and socket resets.
   - **Action Taken:** Enforced `download_policy: "manual_prerequisite"`. Developers must download and extract the required subset manually before running normalization.

3. **NYC 311 Visual Media Absence**:
   - Examination of the live Socrata schema (`erm2-nwe9`) confirms 48 attributes with zero photographic attachment URLs.
   - **Action Taken:** Excluded entirely from visual benchmarking. Retained strictly for civic complaint text pattern analysis.

4. **Boston 311 Verification & Public Domain Clearance**:
   - The City of Boston explicitly dedicates 311 data to the public domain under **ODC-PDDL**.
   - Live CKAN datastore table `1a0b420d-99f1-4887-9851-990b2a5a6e17` provides verified citizen and municipal resolution photos on Cloudinary.
   - **Action Taken:** Selected as the sole source for controlled pilot acquisition.

---

## 3. Controlled Pilot Acquisition Results

Acquisition was executed using `scripts/datasets/download_subsets.py` with strict safety guards:
- **Default mode:** Dry-run metadata inspection only.
- **Execution mode:** Explicit `--execute` flag required.
- **Safety bounds:** `--limit 10`, `--max-bytes 25MB`.

### Acquisition Summary

```
=================================================================
 CIVICSENSE DATASET ACQUISITION PLAN [EXECUTION MODE]
=================================================================
Target Output Directory : datasets/raw
Record Limit Per Source : 10
Max Bytes Per Source    : 25.0 MB
Source Executed         : BOSTON311
Actual Downloaded Files : 10 JPEGs
Total Payload Bytes     : 1,960,015 bytes (1.87 MB)
Network Failures        : 0
HTTP Errors             : 0
=================================================================
```

### Generated Manifests & Staging Files

1. `datasets/raw/download_manifest.json`: Full acquisition audit trail tracking source URLs, acquisition modes, sha256 checksums, byte counts, and legal attribution.
2. `datasets/raw/boston311/raw_samples.json`: 10 candidate records with source record IDs, categories, text descriptions, and Cloudinary URLs.
3. `datasets/raw/boston311/images/`: 10 downloaded JPEG image files.

---

## 4. Defensive Image Validation Results

All 10 downloaded images were subjected to two-phase validation via `scripts/datasets/validate_images.py`:

- **Path traversal prevention:** Resolved against base directory boundary.
- **File size bounds:** Enforced within [100 bytes, 10 MB]. (Smallest: 117 KB, Largest: 299 KB).
- **Magic bytes inspection:** Verified standard JPEG SOI marker `0xFF 0xD8 0xFF`.
- **Pillow full stream decode:** 100% full pixel stream decode completed; 0 corrupt files.
- **Decompression bomb check:** Pixel counts (995,328 pixels) well below 25,000,000 threshold.
- **Dimension bounds:** All images are 864 x 1152 px, safely within [64, 8192] px bounds.
- **Perceptual quality checks:** 0 blurry images flagged, 0 low-resolution images flagged.
- **Hashes computed:** Cryptographic SHA-256 and 64-bit gradient difference hash (`dHash`).

Validation report written to `datasets/raw/boston311/validation_report.json`.

---

## 5. Deduplication & Perceptual Distance Analysis

Two-phase deduplication was performed via `scripts/datasets/deduplicate_benchmark.py`:

1. **Exact Deduplication (SHA-256)**:
   - 10 distinct cryptographic hashes across 10 files.
   - Exact duplicates: **0**.

2. **Near-Duplicate Perceptual Analysis (64-bit dHash)**:
   - Evaluated pairwise Hamming distances across all 45 pairs.
   - Threshold for near-duplicates: Hamming distance <= 4 bits.
   - **Minimum observed Hamming distance:** **23 bits** (between `pilot_bost311_101006649157` and `pilot_bost311_101006636906`).
   - **Mean observed Hamming distance:** **33.6 bits**.
   - Near duplicates flagged: **0**.
   - Total retained unique samples: **10 (100%)**.

---

## 6. Manual Review Catalog (`datasets/raw/manual_review.json`)

To ensure complete legal and technical traceability, `datasets/raw/manual_review.json` was established, cataloging:

1. **TACO License Ambiguity**: Documents the 47.7% null license finding and sets operational gate to `BLOCKED_PENDING_PER_IMAGE_FILTER`.
2. **RDD2022 Packaging**: Documents multi-GB tarball requirement and sets operational gate to `MANUAL_STAGING_PREREQUISITE`.
3. **NYC 311 Media Absence**: Documents zero photo columns in Socrata schema and sets operational gate to `EXCLUDED_FROM_VISUAL_BENCHMARK`.
4. **Boston 311 Water Leakage Deficit**: Documents that water leaks are routed to the independent Boston Water and Sewer Commission (BWSC), leading to a natural scarcity of water leak photos in central city 311 data.
5. **Boston 311 Ambiguous Service Types**: Catalogs municipal types requiring strict rejection (e.g., residential pest complaints, zoning violations, general requests).

---

## 7. Preliminary Pilot Benchmark Assembly (`datasets/benchmark_v1/`)

The preliminary pilot benchmark was assembled using `scripts/datasets/curate_benchmark.py`:
- Target per category: 50.
- Images standardized and copied to: `datasets/benchmark_v1/images/` (10 JPEGs named by sample ID).
- Line-delimited canonical dataset: `datasets/benchmark_v1/benchmark_dataset.jsonl`.
- Manifest file: `datasets/benchmark_v1/manifest.json`.
- Curation audit report: `datasets/benchmark_v1/curation_report.json`.

### Category Distribution & Shortage Preservation

| Canonical Category | Target Quota | Actual Curated Count | Shortage | Shortage Handled By |
| :--- | :---: | :---: | :---: | :--- |
| **Pothole** | 50 | 1 | -49 | Real count retained; zero synthetic padding |
| **Garbage** | 50 | 3 | -47 | Real count retained; zero synthetic padding |
| **Water Leakage** | 50 | 0 | -50 | Real count retained; zero synthetic padding |
| **Streetlight** | 50 | 2 | -48 | Real count retained; zero synthetic padding |
| **Road Damage** | 50 | 2 | -48 | Real count retained; zero synthetic padding |
| **Other** | 50 | 2 | -48 | Real count retained; zero synthetic padding |
| **Total** | **300** | **10** | **-290** | **Honest Shortage Preserved** |

---

## 8. Dataset Quality & Balance Analysis (`datasets/reports/dataset_report.json`)

Generated via `scripts/datasets/report_dataset.py`:

- **Total Samples:** 10
- **Balanced at Target (50/cat):** NO (Shortage of 290 across 6 canonical classes)
- **Source Distribution:** 100% Boston 311
- **License Distribution:** 100% ODC-PDDL (Public Domain)
- **Data Completeness:**
  - Missing text descriptions: 0
  - Missing image paths: 0
  - Missing attributions: 0
- **Quality Flags:**
  - Blurry images: 0
  - Low-resolution images: 0

---

## 9. Acceptance Checklist for Baseline Evaluation Eligibility

Before executing any baseline evaluation of the deterministic AI pipeline, the following gate criteria must be evaluated:

| Criterion | Status | Finding / Blocker |
| :--- | :---: | :--- |
| **1. Legally cleared source licenses** | ⚠️ PARTIAL | Boston 311 cleared (ODC-PDDL); TACO blocked pending per-image license filter; RDD2022 requires manual extraction. |
| **2. Target 300 samples (50/class)** | ❌ BLOCKED | Current dataset has 10 pilot samples; shortage of 290 samples across categories. |
| **3. All 6 canonical classes represented** | ❌ BLOCKED | Water Leakage has 0 samples (Boston 311 CRM routes water leaks to BWSC). |
| **4. Zero image corruption / decoding failures** | ✅ PASSED | 10/10 pilot images decode cleanly with zero errors or warnings. |
| **5. Deduplication verification** | ✅ PASSED | 0 exact duplicates, 0 near-duplicates (min dHash distance 23 bits). |
| **6. Evaluation infrastructure verified** | ✅ PASSED | `OfflineDeterministicEvaluator`, `BenchmarkRunner`, and `calculate_classification_metrics` all passing automated tests. |

### Baseline Evaluation Determination: **NOT ELIGIBLE YET**

**Rationale:**  
Evaluating the deterministic baseline on a 10-sample pilot with 0 water leakage samples would yield statistically unrepresentative, distorted metrics (e.g. 0% support for Water Leakage, arbitrary accuracy variances). Per AGENTS.md Section 6, we must not fabricate baseline numbers.

### Required Actions Before Baseline Evaluation:
1. Implement per-image CC-BY license filter in `curate_benchmark.py` to ingest verified TACO images for `Garbage` (target: 50).
2. Manually stage RDD2022 `India.tgz` subset into `datasets/raw/rdd2022/` for `Pothole` and `Road Damage` (target: 50 each).
3. Identify a dedicated open source for `Water Leakage` (target: 50) to address the municipal CRM routing deficit.
4. Scale Boston 311 acquisition to reach 50 samples each for `Streetlight` and `Other`.
5. Once 300 balanced samples (50 per category) are assembled and validated, run `BenchmarkRunner`.

---

## 10. Automated Validation & Test Suite

| Test Suite / Tool | Command | Result |
| :--- | :--- | :--- |
| **Dataset Tooling Unit Tests** | `pytest tests/unit/test_dataset_tooling.py` | **11 / 11 PASSED** (100%) |
| **Full Backend Test Suite** | `pytest` | **118 / 118 PASSED** (100%) |
| **Ruff Linter & Formatter** | `ruff check . ../scripts/datasets` | **0 errors, all checks passed** |
| **Mypy Static Type Checker** | `mypy ../scripts/datasets app tests` | **0 issues across 111 source files** |

---

## 11. Artifact Integrity & File Status

- `datasets/raw/download_manifest.json`: Verified JSON manifest tracking pilot acquisition.
- `datasets/raw/boston311/images/`: 10 verified JPEG images (1.87 MB).
- `datasets/raw/boston311/raw_samples.json`: 10 candidate metadata records.
- `datasets/raw/boston311/validation_report.json`: Image validation report.
- `datasets/raw/manual_review.json`: Audit catalog of ambiguous/blocked candidate sources.
- `datasets/benchmark_v1/images/`: 10 standardized benchmark images (`pilot_bost311_*.jpg`).
- `datasets/benchmark_v1/benchmark_dataset.jsonl`: 10 canonical evaluation records.
- `datasets/benchmark_v1/manifest.json`: Benchmark manifest.
- `datasets/benchmark_v1/curation_report.json`: Curation report preserving category shortages.
- `datasets/reports/dataset_report.json`: Dataset quality and balance audit report.
- `memory.md`: Updated to record Phase 3.2 Step 4A facts.
