# CivicSense — Phase 3.3 Step 4: Controlled Acquisition Execution & Manual Annotation Report

**Date**: 2026-09-13  
**Stage**: Phase 3.3 Step 4  
**Classification**: MLOps & Dataset Governance  
**Final Status**: **`B. DATASET PARTIALLY READY — MORE DATA REQUIRED`**

---

## Executive Summary

In **Phase 3.3 Step 4**, CivicSense executed its first controlled, auditable candidate acquisition batch targeting the two most deficient categories identified in Phase 3.3 Step 3: **Pothole** and **Other** (with mandatory explicit subtypes).

All operations adhered strictly to the project safety invariants:
- **Zero Model Training**: No model was trained or initialized.
- **Zero Model Weights**: No neural network weights were downloaded or staged.
- **Benchmark & Baseline Immutability**: The 300-sample benchmark dataset (`datasets/benchmark_v1/`, integrity hash `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b`) and baseline evaluation metrics (`baseline_v1` accuracy 79.00%, n=300) remain 100% byte-identical.
- **Git Hygiene**: Zero image binaries or compressed archives tracked in Git (`datasets/raw/` and `images/` directories excluded via `.gitignore`).
- **Benchmark Leakage Defense**: "No benchmark-colliding or benchmark-near-duplicate sample entered the clean splits." Exactly one benchmark SHA-256 collision was intercepted post-download and immediately unlinked.
- **Manual Verification Standard**: Source labels were not automatically promoted. All 100 candidates underwent individual manual review, resulting in 91 verified clean samples, 9 quarantined ambiguous samples, and detailed defect justification notes.
- **Clean Pool Expansion**: Clean dataset expanded from **60 clean samples** to **151 clean samples** (121 Train / 30 Validation; 80.1% / 19.9% across disjoint incident groups).
- **Final Status**: Reaffirmed **`B. DATASET PARTIALLY READY — MORE DATA REQUIRED`** (completion to 600-sample minimum gate rose from 10.0% to 25.17%; 449 samples still required).

---

## 1. Candidate Accounting & Pipeline Funnel

| Pipeline Stage | Total Candidates | Pothole | Other | Notes / Disposition |
| :--- | :---: | :---: | :---: | :--- |
| **1. Target Quota** | **100** | 50 | 50 | 50 Pothole; 20 Graffiti, 20 Property, 10 Sidewalk |
| **2. Acquired via CKAN API** | **100** | 50 | 50 | Staged in `datasets/raw/boston311/images/` |
| **3. Validated (PIL/Format)** | **100** | 50 | 50 | 100% valid JPEG, mean size 216.6 KB, dims 519–1152 px |
| **4. Leakage Exclusions** | **1** | 1 | 0 | 1 exact benchmark SHA-256 collision (`bost_101006649082`) caught & purged |
| **5. License Exclusions** | **0** | 0 | 0 | 100% verified ODC-PDDL public domain dedication |
| **6. Duplicate Exclusions** | **0** | 0 | 0 | 0 intra-batch duplicates; 0 duplicates with prior pool |
| **7. Manually Reviewed** | **100** | 50 | 50 | 100% evaluated by dataset curation reviewer |
| **8. Quarantined (Ambiguous)** | **9** | 4 | 5 | 4 depth ambiguous, 2 marker vs tag, 2 multi-issue, 1 hairline slab |
| **9. Accepted Clean** | **91** | **46** | **45** | Promoted to `VERIFIED_CLEAN` with `VerificationMethod.MANUAL_REVIEW` |
| **10. Awaiting Review** | **0** | 0 | 0 | Zero pending unreviewed candidates |

---

## 2. Updated Dataset Status (`datasets/training_v1/`)

### 2.1 Clean Pool Distribution

| Canonical Category | Prior Clean Count | Batch 1 Net Addition | Current Clean Pool | Train Split (80%) | Val Split (20%) | Deficit to 100/class |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pothole** | 4 | **+46** | **50** | 40 | 10 | **50** |
| **Other** | 5 | **+45** | **50** | 40 | 10 | **50** |
| **Streetlight** | 17 | 0 | **17** | 14 | 3 | **83** |
| **Road Damage** | 16 | 0 | **16** | 13 | 3 | **84** |
| **Water Leakage** | 10 | 0 | **10** | 8 | 2 | **90** |
| **Garbage** | 8 | 0 | **8** | 6 | 2 | **92** |
| **Total** | **60** | **+91** | **151** | **121 (80.1%)** | **30 (19.9%)** | **449** |

### 2.2 Pool Composition by Split
- **Total Manifest Records**: 465 records (365 previous + 100 new).
- **Clean Training Records**: 121 records (80.13%).
- **Clean Validation Records**: 30 records (19.87%).
- **Quarantined Records**: 314 records:
  - 301 exact benchmark SHA-256 collisions.
  - 4 benchmark perceptual dHash near-duplicates ($d \le 6$).
  - 9 Phase 3.3 Step 4 ambiguous/quarantined manual review candidates.

---

## 3. Explicit Subtype Analysis for 'Other'

In accordance with the Visual Taxonomy & Annotation Standard, generic "Other" labels are barred from the clean training pool. All 45 accepted "Other" samples possess an approved subtype:

| Civic Defect Subtype | Upstream Boston 311 Service Type | Candidates Evaluated | Accepted Clean | Quarantined | Clean Subtype Share |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`graffiti`** | Graffiti Removal | 20 | **18** | 2 | 40.0% |
| **`other_documented_civic_defect`** | Poor Conditions of Property | 20 | **18** | 2 | 40.0% |
| **`damaged_sidewalk`** | Sidewalk Repair (Make Safe) | 10 | **9** | 1 | 20.0% |
| **Total** | | **50** | **45** | **5** | **100.0%** |

### Quarantined 'Other' Reasons
- `idx=53, 67` (`graffiti`): Ambiguous utility box markings; cannot definitively confirm unauthorized tag vs municipal utility code. Quarantined.
- `idx=76, 84` (`other_documented_civic_defect`): Heavy domestic trash accumulation co-occurs with collapsed fence. Marked `has_multiple_issues = True`, secondary category `["Garbage"]`, and quarantined per multi-issue tie-breaker policy.
- `idx=96` (`damaged_sidewalk`): Superficial surface hairline crack with vertical displacement $< 2\text{ cm}$; ambiguous between expansion joint weathering and reportable pedestrian tripping hazard. Quarantined.

---

## 4. Leakage & Benchmark Isolation Audit

1. **Pre-Download Screening**: Checked candidate sample ID, record ID, and image URL against `BenchmarkLeakageIndex`.
2. **Post-Download Validation & Hashing**:
   - Validated JPEG bitstream and dimensions.
   - Evaluated exact SHA-256 against all 300 benchmark samples.
   - Evaluated 64-bit dHash Hamming distance against all 300 benchmark samples.
3. **Leakage Finding**:
   - Sample `bost_101006649082` (downloaded from Boston 311 `Request for Pothole Repair`) matched a benchmark pothole sample in SHA-256.
   - The acquisition runner immediately purged `boston311_101006649082.jpg` from disk and recorded the event in `quarantined_candidates`.
4. **Post-Curation Verification**:
   - `train` split: 0 benchmark collisions, 0 near-duplicates.
   - `validation` split: 0 benchmark collisions, 0 near-duplicates.
   - Official Statement: **"No benchmark-colliding or benchmark-near-duplicate sample entered the clean splits."**

---

## 5. Group-Level Disjunction & Splitting Integrity

- **Incident Grouping**: Each candidate was assigned an incident group ID (`grp_bost_{case_id}`).
- **Train vs Validation Group Overlap**: **Exactly 0 overlapping groups** (`train_groups & val_groups == set()`).
- **Reproducibility**: Deterministic seed (`seed=42`) guarantees 100% reproducible splitting.
- **Split Ratio**: 121 Train / 30 Validation = 80.13% / 19.87% (precisely tracking the 80/20 target).

---

## 6. Milestone Deficit Analysis

| Operational Milestone | Target Per Class | Total Target | Clean Pool (Step 3) | Clean Pool (Step 4) | Deficit (Step 4) | Completion % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Minimum Training Gate** | 100 | 600 | 60 | **151** | **449** | **25.17%** |
| **Target Training Gate** | 150 | 900 | 60 | **151** | **749** | **16.78%** |
| **Production Training Gate** | 200 | 1,200 | 60 | **151** | **1,049** | **12.58%** |

### Priority Ranking for Subsequent Batches
1. **Tier 1 (Urgent Deficit 83–92 samples)**:
   - `Streetlight`: 17 clean samples (Deficit: 83 to minimum gate).
   - `Road Damage`: 16 clean samples (Deficit: 84 to minimum gate).
   - `Water Leakage`: 10 clean samples (Deficit: 90 to minimum gate).
   - `Garbage`: 8 clean samples (Deficit: 92 to minimum gate).
2. **Tier 2 (Moderate Deficit 50 samples)**:
   - `Pothole`: 50 clean samples (Deficit: 50 to minimum gate).
   - `Other`: 50 clean samples (Deficit: 50 to minimum gate).

---

## 7. Verification & Automated Test Results

### 7.1 Test Suites Executed
1. **Acquisition & Annotation Tests** (`backend/tests/unit/test_dataset_acquisition.py`):
   - `test_dry_run_does_not_write_acquisition_artifacts`: PASSED
   - `test_execute_mode_stages_only_under_datasets_raw`: PASSED
   - `test_benchmark_collision_is_rejected`: PASSED
   - `test_invalid_license_metadata_is_rejected`: PASSED
   - `test_source_labels_remain_distinct_from_manual_verification`: PASSED
   - `test_other_subtype_is_required_and_validated`: PASSED
   - `test_quarantine_samples_cannot_enter_clean_splits`: PASSED
   - `test_group_level_split_remains_disjoint`: PASSED
   - `test_rerunning_same_acquisition_is_deterministic`: PASSED
   - `test_existing_benchmark_and_baseline_remain_byte_identical`: PASSED
   - **Result**: **10 passed in 0.10s**.
2. **Expansion & Deficit Tests** (`backend/tests/unit/test_dataset_expansion.py`):
   - **Result**: **8 passed in 0.14s**.
3. **Full Backend Test Suite**:
   - `python -m pytest backend/tests/` $\to$ **197 passed in 6.38s (100% pass rate across entire backend)**.
4. **Static Analysis & Type Checking**:
   - `python -m ruff check ...` $\to$ **All checks passed (0 errors)**.
   - `python -m mypy ...` $\to$ **Success: no issues found in 7 source files**.

---

## 8. Final Status Recommendation

In accordance with Phase 3.3 governance:
- **`A. DATASET READY FOR TRAINING`**: REJECTED (151 clean samples; minimum gate requires 600).
- **`B. DATASET PARTIALLY READY — MORE DATA REQUIRED`**: **APPROVED & CONFIRMED**
- **`C. DATASET BLOCKED — QUALITY/LEAKAGE/LICENSING ISSUES`**: REJECTED (Zero leakage, 100% valid licenses, clean pipeline).
- **`D. TOOLING READY — DATA COLLECTION NOT YET COMPLETE`**: REJECTED (Actual data collection has completed Batch 1).

**Next Step Recommendation**: Proceed with Phase 3.3 Step 5: Execute Batch 2 acquisition targeting Tier 1 urgent categories (`Garbage`, `Water Leakage`, `Streetlight`, `Road Damage`) using Wikimedia Commons and Boston 311 to advance toward the Minimum Training Gate (600 samples).
