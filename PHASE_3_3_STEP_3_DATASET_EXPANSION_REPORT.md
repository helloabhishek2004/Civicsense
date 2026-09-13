# CivicSense — Phase 3.3 Step 3: Controlled Training Dataset Expansion & Quality Audit Report

**Date**: 2026-09-13  
**Stage**: Phase 3.3 Step 3  
**Classification**: MLOps & Dataset Governance  
**Final Status**: **`B. DATASET PARTIALLY READY — MORE DATA REQUIRED`**

---

## Executive Summary

Phase 3.3 Step 3 performed a rigorous audit of the training dataset foundation established in Phase 3.3 Step 2, conducted independent forensic validation of all benchmark isolation and governance claims, performed comprehensive class deficit calculations across operational milestones, formulated a multi-source acquisition plan from legally vetted open repositories, implemented production-grade controlled expansion tooling, and codified strict quality gates.

**Key Findings**:
- **Clean Training Pool**: Exactly **60 samples** (48 Train, 12 Validation; 80.0% / 20.0% split across 60 disjoint evidence groups).
- **Quarantined Pool**: **305 samples** correctly quarantined (301 exact SHA-256 benchmark collisions, 4 benchmark dHash perceptual near-duplicates; 0 leakage).
- **Benchmark & Baseline Immutability**: Benchmark manifest hash (`e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b`) and baseline evaluation metrics (`baseline_v1` accuracy 79.00%, n=300) remain 100% intact and untouched.
- **Git Hygiene**: Zero image binaries tracked in git; zero model weights downloaded or present; zero model training executed.
- **Deficit Analysis**:
  - Minimum Training Gate (100/class = 600 samples): **540 samples needed** (10.0% progress).
  - Target Training Gate (150/class = 900 samples): **840 samples needed** (6.7% progress).
  - Production Gate (200/class = 1,200 samples): **1,140 samples needed** (5.0% progress).
- **Most Deficient Categories**: `Pothole` (4 clean samples, deficit 96/146/196) and `Other` (5 clean samples, deficit 95/145/195).

---

## 1. Phase 1 — Manifest & Report Audit

### 1.1 Category Distribution Across Splits

| Canonical Category | Total Candidates | Quarantined | Clean Pool | Train Split | Val Split | Deficit to 100/class |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pothole** | 54 | 50 | **4** | 3 | 1 | **96** |
| **Road Damage** | 66 | 50 | **16** | 13 | 3 | **84** |
| **Garbage** | 58 | 50 | **8** | 6 | 2 | **92** |
| **Water Leakage** | 60 | 50 | **10** | 8 | 2 | **90** |
| **Streetlight** | 67 | 50 | **17** | 14 | 3 | **83** |
| **Other** | 60 | 55 | **5** | 4 | 1 | **95** |
| **Total** | **365** | **305** | **60** | **48 (80.0%)** | **12 (20.0%)** | **540** |

### 1.2 Verification Breakdown
- **Source Verified**: 60 / 60 clean samples (100.0%).
- **Manual Expert Verified**: 0 / 60 (pending expansion review workflows).
- **Direct Visual Relevance**: 60 / 60 clean samples (100.0%).

### 1.3 Source Distribution

| Source Dataset | Total Ingested | Quarantined | Clean Pool | % of Clean Pool |
| :--- | :---: | :---: | :---: | :---: |
| `boston311` | 315 | 255 | 60 | 100.0% |
| `wikimedia_commons` | 50 | 50 | 0 | 0.0% |
| **Total** | **365** | **305** | **60** | **100.0%** |

*Note*: 100% of Wikimedia Commons pilot samples collided with benchmark v1 because the initial candidate pool re-examined earlier pilot ingestion logs. Controlled expansion will query fresh, unharvested record partitions.

### 1.4 Quarantine Reasons Breakdown
- **Exact SHA-256 Collision with Benchmark**: 301 records (98.69%).
- **dHash Perceptual Near-Duplicate with Benchmark (Hamming Distance ≤ 6)**: 4 records (1.31%).
  - 1 Pothole candidate
  - 1 Garbage candidate
  - 2 Other candidates
- **Total Quarantined**: 305 records.

### 1.5 Image & Resolution Quality Metrics (Clean Pool)
- **Width Range**: 640 px to 3,024 px (Mean: 2,058.4 px).
- **Height Range**: 480 px to 4,032 px (Mean: 2,528.9 px).
- **File Size Range**: 67.2 KB to 5,595.6 KB (Mean: 1,326.6 KB).
- **Aspect Ratio Range**: 0.75 (3:4 portrait) to 1.33 (4:3 landscape) — zero extreme aspect-ratio outliers.
- **Image Corruption / Decompression Bomb**: 0 / 60 (100% valid JPEG/PNG).

### 1.6 Evidence Grouping Statistics
- **Total Unique Evidence Groups**: 60.
- **Singleton Groups**: 60 (100.0% singleton; 1 sample per group).
- **Train Groups**: 48.
- **Validation Groups**: 12.
- **Group Leakage**: 0 (0% overlap between train and validation groups).

---

## 2. Phase 2 — Independent Claim Validation (11 Invariants)

All 11 claims from the Phase 3.3 Step 2 specification were independently tested and verified against actual filesystem contents:

| Claim # | Claim Description | Verification Method | Result | Status |
| :--- | :--- | :--- | :---: | :---: |
| **1** | No exact benchmark collision in `train` split | SHA-256 cross-check against benchmark manifest | 0 collisions | **VERIFIED** |
| **2** | No exact benchmark collision in `validation` split | SHA-256 cross-check against benchmark manifest | 0 collisions | **VERIFIED** |
| **3** | No benchmark near-duplicate in `train` split | dHash Hamming distance calculation (threshold ≤ 6) | 0 near-duplicates | **VERIFIED** |
| **4** | No benchmark near-duplicate in `validation` split | dHash Hamming distance calculation (threshold ≤ 6) | 0 near-duplicates | **VERIFIED** |
| **5** | Zero group leakage between `train` and `validation` | Group ID intersection (`train_groups & val_groups`) | 0 overlapping groups | **VERIFIED** |
| **6** | No quarantined sample in `train` or `validation` | ID intersection between clean splits and quarantine | 0 quarantined samples | **VERIFIED** |
| **7** | Benchmark dataset integrity hash unchanged | SHA-256 of `benchmark_dataset.jsonl` matching `manifest.json` | `e988474d...fd2e60b` | **VERIFIED** |
| **8** | Baseline evaluation metrics intact | Inspected `baseline_v1/metrics.json` | Acc: 79.00%, n=300 | **VERIFIED** |
| **9** | Zero training image binaries in git index | `git ls-files datasets/` checked for binary formats | 0 binaries in git | **VERIFIED** |
| **10** | Zero model weights downloaded or present | Checked repo for `.pt`, `.pth`, `.onnx`, `.tflite` | 0 weights found | **VERIFIED** |
| **11** | Zero model training occurred | Confirmed training runner not implemented | 0 training runs | **VERIFIED** |

---

## 3. Phase 3 — Class Deficit Analysis

### 3.1 Milestone Target Comparison

| Category | Current Clean | Milestone 1 (100/cat) Deficit | Milestone 2 (150/cat) Deficit | Milestone 3 (200/cat) Deficit | Current % of Target (Milestone 1) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Pothole** | 4 | **96** | 146 | 196 | 4.0% |
| **Other** | 5 | **95** | 145 | 195 | 5.0% |
| **Garbage** | 8 | **92** | 142 | 192 | 8.0% |
| **Water Leakage** | 10 | **90** | 140 | 190 | 10.0% |
| **Road Damage** | 16 | **84** | 134 | 184 | 16.0% |
| **Streetlight** | 17 | **83** | 133 | 183 | 17.0% |
| **Total Pool** | **60** | **540** | **840** | **1,140** | **10.0%** |

### 3.2 Category Priority Ranking
1. **Tier 1 (Urgent Deficit < 10 samples)**:
   - `Pothole`: 4 clean samples (Deficit: 96 to min gate).
   - `Other`: 5 clean samples (Deficit: 95 to min gate).
2. **Tier 2 (High Deficit 8–10 samples)**:
   - `Garbage`: 8 clean samples (Deficit: 92 to min gate).
   - `Water Leakage`: 10 clean samples (Deficit: 90 to min gate).
3. **Tier 3 (Moderate Deficit 16–17 samples)**:
   - `Road Damage`: 16 clean samples (Deficit: 84 to min gate).
   - `Streetlight`: 17 clean samples (Deficit: 83 to min gate).

---

## 4. Phase 4 — Source Acquisition Plan

Documented in [`docs/ML_DATASET_ACQUISITION_PLAN_V1.md`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/docs/ML_DATASET_ACQUISITION_PLAN_V1.md).

### Summary of Legally Vetted Repositories

| Repository | Primary Target Categories | License | API / Access Protocol | Rate Limits & Ingestion Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Analyze Boston (311)** | `Pothole`, `Garbage`, `Road Damage`, `Streetlight`, `Other` | ODC-PDDL (Public Domain Dedication) | CKAN REST API (`datastore_search`) | ≤ 2 req/sec, max 100 rec/batch. Pre-filter on `submittedphoto IS NOT NULL`. Exclude benchmark record IDs. |
| **Wikimedia Commons** | `Water Leakage`, `Pothole`, `Road Damage`, `Streetlight` | CC0, CC-BY 2.0/3.0/4.0, CC-BY-SA 4.0 | MediaWiki Action API (`action=query`) | Descriptive User-Agent mandatory, max 1 req/sec. Strict license URL check and near-duplicate dHash comparison. |
| **TACO (Trash Annotations in Context)** | `Garbage` (Municipal litter, waste containers, street trash) | CC-BY 4.0 | COCO format annotation download | 1,500 annotated images. Bounding-box crop option to ensure direct visual relevance. |
| **Geograph Britain and Ireland** | `Road Damage`, `Streetlight`, `Pothole` | CC-BY-SA 2.0 | Geograph API (`geograph.org.uk/api`) | High geospatial metadata quality, requires author attribution, max 1 req/sec. |

---

## 5. Phase 5 — Controlled Acquisition Tooling

Implemented in [`scripts/datasets/controlled_expansion.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/scripts/datasets/controlled_expansion.py).

### Core Architecture & Safety Features
1. **Dry-Run by Default**:
   - `python scripts/datasets/controlled_expansion.py --source boston311 --category Pothole --limit 10` runs in dry-run mode and prints the acquisition plan.
   - Network fetches and writes require explicit `--execute` flag.
2. **Pre-Download Leakage Defense**:
   - Cross-references incoming record identifiers (`source_record_id`, URL) against `BenchmarkLeakageIndex` before initiating image payload transfer.
3. **Post-Download Validation & Perceptual Check**:
   - Downloads image into memory with size limit (max 10 MB).
   - Validates PIL decoding, dimensions, and computes SHA-256 + dHash.
   - Computes dHash Hamming distance against all 300 benchmark samples; immediately deletes image if Hamming distance ≤ 6.
4. **Rate Limiting & Exponential Backoff**:
   - Configurable per-request delay (`--delay-sec 0.5`) and retry logic (`--max-retries 3`).
5. **Raw Quarantine & Isolation**:
   - Acquired candidates are written exclusively to `datasets/raw/<source>/` and never directly into `datasets/training_v1/splits/`.
   - Ingestion into clean splits requires running the curator pipeline (`curate_training_dataset.py`).

---

## 6. Phase 6 — Objective Quality Gates

### Gate Specifications

| Quality Gate | Total Clean Samples | Per-Class Target | Validation Split | Balance Ratio | Ready for Model Training? |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Pilot Training Gate** | 300 | 50 | 20% (60 val) | Max 1.5:1 | Conditional: Baseline fine-tuning feasibility check only |
| **Minimum Training Gate** | 600 | 100 | 20% (120 val) | Max 1.3:1 | **YES**: Viable for MobileNetV3-Small transfer learning |
| **Production Training Gate** | 1,200 | 200 | 20% (240 val) | Max 1.2:1 | **YES**: Recommended for field deployment and authority triage |

### Gate Evaluation Summary
- **Current Dataset Status**: **FAIL (Gate Not Reached)**
  - Total Clean: 60 / 600 (10.0%)
  - Balance Ratio: 4.25:1 (Streetlight 17 vs Pothole 4) — exceeds max permitted ratio (1.3:1)
  - Minimum class count: 4 (Target: 100)
- **Status Clearance**: Training is **BLOCKED** until Minimum Training Gate (600 samples, 100/class) is satisfied.

---

## 7. Verification & Test Execution

### 7.1 Unit & Integration Test Suite
Implemented comprehensive expansion tests in [`backend/tests/unit/test_dataset_expansion.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/tests/unit/test_dataset_expansion.py):
1. `test_deficit_calculation_and_targets`: Validates deficit mathematics across all canonical categories and milestones.
2. `test_priority_ranking_identifies_weakest_categories`: Confirms Pothole and Other are identified as highest priority.
3. `test_pre_download_leakage_check_catches_benchmark_ids`: Verifies benchmark record IDs are caught pre-download.
4. `test_post_download_leakage_check_catches_near_duplicate`: Verifies dHash near-duplicate catches visually similar benchmark images.
5. `test_quality_audit_report_contains_governance_invariants`: Verifies audit reports reflect frozen benchmark state.
6. `test_controlled_expansion_runner_dry_run_safety`: Verifies dry-run executes without network or file side-effects.
7. `test_quality_gates_evaluation`: Validates evaluation logic for pilot, minimum, and production gates.
8. `test_source_registry_documentation_completeness`: Validates metadata and license URLs across registered sources.

### 7.2 Test Execution Results
- `python -m pytest backend/tests/unit/test_dataset_expansion.py` $\to$ **8 passed in 0.14s**.
- `python -m pytest backend/tests/` $\to$ **187 passed in 6.28s (100% pass rate, 0 regressions)**.
- `python -m ruff check ...` $\to$ **All checks passed (0 errors)**.
- `python -m mypy ...` $\to$ **Success: no issues found in 3 source files**.

---

## 8. Final Status Recommendation

In accordance with Phase 3.3 governance:
- **`A. DATASET READY FOR TRAINING`**: REJECTED (Dataset has 60 clean samples; minimum gate requires 600).
- **`B. DATASET PARTIALLY READY — MORE DATA REQUIRED`**: **APPROVED & CONFIRMED**
- **`C. DATASET NOT READY / CRITICAL ISSUES`**: REJECTED (Zero leakage, zero corruption, clear acquisition path established).

**Next Step Recommendation**: Proceed with Phase 3.3 Step 4: Execute controlled batch acquisition via `scripts/datasets/controlled_expansion.py` targeting Tier 1 categories (`Pothole` and `Other`) from Boston 311 and Wikimedia Commons to satisfy the Minimum Training Gate.
