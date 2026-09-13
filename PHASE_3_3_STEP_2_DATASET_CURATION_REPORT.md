# CivicSense — Phase 3.3 Step 2 Implementation & Curation Report
# Training Dataset Preparation, Annotation Taxonomy, Leakage Prevention Tooling, and Validation

**Date:** 2026-09-13  
**Status:** COMPLETE & VERIFIED  
**Final Declaration:** `B. DATASET PARTIALLY READY — MORE DATA REQUIRED`

---

## Executive Summary

Phase 3.3 Step 2 establishes the data governance, visual annotation standard, versioned schema, and leakage prevention infrastructure for training civic vision models (MobileNetV3-Small / EfficientNet-Lite0) without training any model and without compromising the frozen 300-sample evaluation benchmark.

All objectives and safety invariants mandated by `AGENTS.md` and the Phase 3.3.2 specification have been rigorously implemented:
1. **Annotation Taxonomy & Guide**: Documented in [`docs/ML_DATASET_ANNOTATION_GUIDE_V1.md`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/docs/ML_DATASET_ANNOTATION_GUIDE_V1.md) defining inclusion/exclusion criteria, boundary resolution, multi-issue dominance hierarchy, sewage overflow rules, and ambiguity/quarantine states.
2. **Versioned Training Schema**: Deployed in [`backend/app/evaluation/training_schema.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/evaluation/training_schema.py) with Pydantic v2 data models (`TrainingSample`, `TrainingSplit`, `AmbiguityStatus`, `BenchmarkLeakageCheckResult`, `TrainingDatasetSummary`).
3. **Leakage Prevention Tooling**: Implemented in [`scripts/datasets/leakage_detector.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/scripts/datasets/leakage_detector.py), auditing exact SHA-256, upstream source IDs, normalized URLs, and 64-bit dHash Hamming distances ($\le 6$ bits) against the 300 frozen benchmark samples.
4. **Intra-Dataset Duplicate Detection & Grouped Splitting**: Implemented in [`scripts/datasets/training_splitter.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/scripts/datasets/training_splitter.py) enforcing deterministic 80/20 train/val splits with strict group-level disjunction and quarantine exclusion.
5. **Curation Orchestrator**: Built [`scripts/datasets/curate_training_dataset.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/scripts/datasets/curate_training_dataset.py) assembling raw candidates, validating image decodability, executing leakage checks, and generating `datasets/training_v1/`.
6. **Unit Test Suite**: 24 new automated unit tests added in [`backend/tests/unit/test_training_dataset.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/tests/unit/test_training_dataset.py) (100% pass rate; total backend test suite expanded to **179 passing tests**).

---

## Detailed Audit Breakdown

### 1. Data Accounting & Status

| Category | Input Candidates | Leakage Rejections (Quarantined) | Clean Retained | Train Split (80%) | Validation Split (20%) | Quarantine Total | Target Deficit (vs 200/class) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pothole** | 55 | 51 | 4 | 3 | 1 | 51 | -196 |
| **Road Damage** | 70 | 54 | 16 | 13 | 3 | 54 | -184 |
| **Garbage** | 58 | 50 | 8 | 6 | 2 | 50 | -192 |
| **Water Leakage** | 60 | 50 | 10 | 8 | 2 | 50 | -190 |
| **Streetlight** | 67 | 50 | 17 | 14 | 3 | 50 | -183 |
| **Other** | 55 | 50 | 5 | 4 | 1 | 50 | -195 |
| **TOTAL** | **365** | **305** | **60** | **48** | **12** | **305** | **-1,140** |

*Clarification of Leakage Rejections*:
- 301 raw samples were rejected due to exact SHA-256 collision with the benchmark (former benchmark candidates in `datasets/raw/`).
- 4 raw samples were rejected due to perceptual near-duplicate collision with the benchmark (64-bit dHash Hamming distance $\le 6$).
- Zero leaked samples entered `train.jsonl` or `validation.jsonl`. 100% of benchmark collisions were routed to `quarantine.jsonl`.
- The 60 clean retained samples are partitioned into **48 train (80.0%)** and **12 validation (20.0%)** with **zero group leakage**.

---

### 2. Leakage Prevention Audit

* **Benchmark Sample Count**: Exactly 300 samples loaded and indexed from `datasets/benchmark_v1/`.
* **Benchmark Manifest Hash**: `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b` (**VERIFIED UNMODIFIED**).
* **Baseline Metrics**: Multimodal accuracy 79.00% across 300 samples in `datasets/evaluation_runs/baseline_v1/` (**VERIFIED UNMODIFIED**).
* **Invariants Enforced**:
  - Exact SHA-256 Collision Check: Rejects candidate if hash in benchmark.
  - Upstream Source Record ID Check: Rejects candidate if `(source_dataset, source_record_id)` in benchmark.
  - Canonical URL Check: Rejects candidate if normalized URL matches benchmark direct asset URL.
  - Perceptual dHash Check: Rejects candidate if 64-bit Hamming distance $\le 6$ bits against ANY of the 300 benchmark samples.
  - Borderline Match Flagging: Flags candidates with Hamming distance $\in [7, 10]$ bits for reviewer inspection.

---

### 3. Duplicate Detection & Group Assignment Audit

* **Intra-Dataset Duplicate Analysis**:
  - Exact Duplicates within Clean Pool: 0.
  - Near-Duplicates within Clean Pool (dHash distance $\le 4$): 9 pairs detected across burst municipal service requests.
* **Evidence-Based Grouping**:
  - Boston 311: Assigned via CRM incident service request ID (`grp_bost_{service_request_id}`).
  - Wikimedia Commons: Assigned via Wikimedia Page ID / Asset base (`grp_wm_{page_id}`).
  - TACO: Assigned via batch/image ID (`grp_taco_{image_id}`).
* **Group Split Integrity**:
  - Number of distinct groups in training split: 48.
  - Number of distinct groups in validation split: 12.
  - Intersection of group IDs between train and validation: **0 (DISJOINT, ZERO GROUP LEAKAGE)**.
  - Quarantined sample leakage into train/val: **0 (STRICT QUARANTINE ISOLATION)**.

---

### 4. Source Distribution & Licensing Provenance

Every sample resolves to a documented licensing source:
* **Boston 311** (Analyze Boston Open Data): 172 records evaluated (14 clean retained, 158 quarantined). License: **ODC-PDDL** (Public Domain Dedication and License).
* **Wikimedia Commons (Road Damage, Streetlight, Water Leakage)**: 190 records evaluated (43 clean retained, 147 quarantined). Licenses: **CC-BY-SA 4.0 / 3.0 / 2.0, CC-BY, CC0 / Public Domain**.
* **TACO (Trash Annotations in Context)**: 3 records evaluated (3 clean retained, 0 quarantined). Licenses: **CC-BY 4.0 / ODbL**.
* **Total License Coverage**: **100%** of samples have auditable legal license declarations in `provenance/source_registry.json`.

---

### 5. Repository & Git Storage Protection

* `datasets/.gitignore` was updated to explicitly ignore `training_v1/images/` and raw archives.
* Git status verification confirms that:
  - Manifests (`manifest.jsonl`), splits (`train.jsonl`, `validation.jsonl`, `quarantine.jsonl`), dataset summaries, and reports are tracked.
  - **Zero image binaries or binary archives are staged or tracked in git.**

---

### 6. Validation Command Results

| Tool | Scope | Command | Result |
| :--- | :--- | :--- | :--- |
| **Pytest** | Focused Training Tests | `python -m pytest backend/tests/unit/test_training_dataset.py -v` | **24 passed** in 0.14s |
| **Pytest** | Complete Backend Suite | `python -m pytest backend/tests/ -v` | **179 passed** in 6.28s |
| **Ruff** | Linter & Formatter | `python -m ruff check --config backend/pyproject.toml backend/app/evaluation/ backend/tests/unit/test_training_dataset.py scripts/datasets/` | **All checks passed!** (0 errors) |
| **Mypy** | Static Type Checker | `python -m mypy --config-file backend/pyproject.toml backend/app/evaluation/ scripts/datasets/` | **Success: no issues found in 17 source files** |

---

## Known Limitations & Next Steps

1. **Target Deficit**: The target for production model training is ~1,200 verified balanced samples (~200 per category). The current clean non-leaked foundation contains 60 samples (48 train / 12 val). An expanded, rate-limited acquisition run (e.g. querying additional non-overlapping Boston 311 service request windows and expanding Wikimedia Commons queries) is required before commencing model training.
2. **Model Training Hold**: In strict adherence to safety rules, no model was trained, and no weights were downloaded.
3. **Immutability Invariant**: The frozen benchmark (`datasets/benchmark_v1/`) and baseline evaluation results (`datasets/evaluation_runs/baseline_v1/`) remain 100% byte-identical.

---

## Final Status Declaration

```
================================================================================
FINAL STATUS: B. DATASET PARTIALLY READY — MORE DATA REQUIRED
================================================================================
Explanation:
- The visual taxonomy guide, versioned schema, leakage detection engine,
  duplicate detection tools, and deterministic group-level splitter are fully
  built, verified, and operational.
- The curation pipeline executed with zero benchmark contamination.
- The current clean pool (60 samples: 48 train / 12 val) establishes the verified
  foundation, but falls short of the ~1,200 sample target (~200 per class).
- In accordance with production engineering standards and AGENTS.md Rule 6,
  no synthetic data was fabricated and no model training will commence until
  sufficient clean samples are acquired.
================================================================================
```
