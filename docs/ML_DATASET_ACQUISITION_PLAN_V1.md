# CivicSense — Controlled Training Dataset Acquisition Plan (v1.0)

**Document Version:** 1.0.0  
**Effective Date:** 2026-09-13  
**Status:** Canonical Dataset Acquisition & Scaling Strategy  
**Target Milestone:** 1,200 Clean Balanced Samples (200/category across 6 canonical classes)

---

## 1. Executive Context & Objectives

Phase 3.3 Step 2 verified the initial foundation for CivicSense's training pool (`datasets/training_v1/`) with 60 clean non-leaked samples (48 train / 12 val) across all six canonical classes. However, an empirical visual classifier (MobileNetV3-Small) requires a larger sample size to achieve stable generalization across real-world urban conditions.

This document defines the legally vetted, technically disciplined acquisition plan to scale CivicSense's training pool across three progressive milestones:
- **Milestone 1 (Pilot Gate):** 300 clean samples (50 per category) — Feasibility fine-tuning.
- **Milestone 2 (Initial Training Gate):** 600 clean samples (100 per category) — Baseline model training.
- **Milestone 3 (Preferred Production Gate):** 1,200 clean samples (200 per category) — Robust, multi-environment deployment.

---

## 2. Current Clean Pool & Deficit Analysis

Based on the audit of `datasets/training_v1/manifest.jsonl`:

| Canonical Category | Clean Pool Total | Train (80%) | Validation (20%) | Shortage to 100/class | Shortage to 150/class | Shortage to 200/class | Priority Tier |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Pothole** | 4 | 3 | 1 | -96 | -146 | -196 | **Tier 1 (Urgent)** |
| **Other** | 5 | 4 | 1 | -95 | -145 | -195 | **Tier 1 (Urgent)** |
| **Garbage** | 8 | 6 | 2 | -92 | -142 | -192 | **Tier 2 (High)** |
| **Water Leakage** | 10 | 8 | 2 | -90 | -140 | -190 | **Tier 2 (High)** |
| **Road Damage** | 16 | 13 | 3 | -84 | -134 | -184 | **Tier 3 (Moderate)** |
| **Streetlight** | 17 | 14 | 3 | -83 | -133 | -183 | **Tier 3 (Moderate)** |
| **TOTAL** | **60** | **48** | **12** | **-540** | **-840** | **-1,140** | — |

---

## 3. Legally Vetted Source Registry & Profiling

In compliance with `AGENTS.md` and production data governance, all training imagery must resolve to documented legal licensing, explicit redistribution permissions, and open-source provenance.

### Source A: City of Boston 311 (Analyze Boston)
* **Official URL:** `https://data.boston.gov/dataset/311-service-requests`
* **API Endpoint:** CKAN Datastore Search API (`https://data.boston.gov/api/3/action/datastore_search`)
* **Legal License:** **ODC-PDDL** (Open Data Commons Public Domain Dedication and License)
* **License URL:** `http://www.opendefinition.org/licenses/odc-pddl`
* **License Scope:** Dataset-level public domain grant.
* **Attribution Requirement:** City of Boston, Analyze Boston Open Data.
* **Redistribution & Derivative Use:** Unrestricted; permits commercial, research, derivative, and model training use.
* **Local Storage Permission:** Explicitly permitted under public domain terms.
* **Rate Limits:** 5 requests per second; recommended batch queries with 1.0s delay.
* **Target Categories:** `Pothole` (`Request for Pothole Repair`), `Garbage` (`Illegal Dumping`), `Other` (`Poor Conditions of Property`, `Graffiti Removal`, `Sign Repair`), `Road Damage` (`Sidewalk Repair (Make Safe)`).
* **Available Supply:** Over 9,000 candidate records with Cloudinary image URLs in public datastore.
* **Label Reliability:** High (standardized municipal CRM intake codes), but citizen upload noise requires automated decodability checks.
* **Duplicate Risk:** Moderate (citizens occasionally submit multiple photos of the same incident). Mitigated by `group_id = f"grp_bost_{service_request_id}"`.
* **Benchmark Overlap Risk:** High (157 Boston 311 records are in `datasets/benchmark_v1/`). Mitigated by mandatory real-time SHA-256, record ID, and dHash leakage checks before staging.

---

### Source B: Wikimedia Commons
* **Official URL:** `https://commons.wikimedia.org`
* **API Endpoint:** MediaWiki Action API (`https://commons.wikimedia.org/w/api.php`)
* **Legal License:** **CC0, CC-BY 4.0/3.0/2.0, CC-BY-SA 4.0/3.0/2.0, Public Domain**
* **License URL:** `https://creativecommons.org/licenses/`
* **License Scope:** Per-image metadata extracted from Wikimedia API `imageinfo`.
* **Attribution Requirement:** Photographer name, source URL, and license title.
* **Redistribution & Derivative Use:** Permitted under CC-BY / CC-BY-SA terms.
* **Local Storage Permission:** Explicitly permitted for local processing.
* **Rate Limits:** 1 request per second; user-agent header mandatory (`CivicSense-Research/1.0`).
* **Target Categories:** `Water Leakage` (`"burst water main"`, `"broken water pipe"`, `"water leak road"`), `Streetlight` (`"broken street light"`, `"damaged lamp post"`), `Road Damage` (`"alligator cracking road"`, `"cracked asphalt"`), `Pothole` (`"road pothole"`).
* **Available Supply:** Hundreds of open-licensed photographs globally.
* **Label Reliability:** Moderate (natural language captions; requires keyword and manual validation).
* **Duplicate Risk:** Low to moderate (galleries by single photographers). Handled by `group_id = f"grp_wm_{page_id}"`.
* **Benchmark Overlap Risk:** Moderate (143 Wikimedia records in benchmark). Mitigated by automated leakage checks.

---

### Source C: TACO (Trash Annotations in Context)
* **Official URL:** `https://github.com/pedropro/TACO`
* **Repository Annotations:** `https://raw.githubusercontent.com/pedropro/TACO/master/data/annotations.json`
* **Legal License:** Strictly filtered for **ODbL (OpenLitterMap)** and **CC-BY** (all unverified or proprietary Flickr licenses excluded).
* **License Scope:** Per-image license field in COCO annotation dictionary.
* **Attribution Requirement:** TACO Project / OpenLitterMap contributors.
* **Redistribution & Derivative Use:** Permitted for academic and open civic model training.
* **Local Storage Permission:** Permitted.
* **Rate Limits:** Direct static JSON read; image downloads rate-limited to 1 request/sec.
* **Target Categories:** `Garbage` (fine-grained litter categories: bottles, cans, paper, plastic).
* **Available Supply:** ~150 verified open-license images.
* **Label Reliability:** High (expert bounding-box annotated).
* **Duplicate Risk:** Low.
* **Benchmark Overlap Risk:** Zero (no TACO images were incorporated into benchmark_v1).

---

### Source D: Geograph Britain and Ireland
* **Official URL:** `https://www.geograph.org.uk/`
* **Legal License:** **CC-BY-SA 2.0**
* **License URL:** `https://creativecommons.org/licenses/by-sa/2.0/`
* **License Scope:** Per-image metadata.
* **Attribution Requirement:** Photographer and Geograph project attribution.
* **Target Categories:** `Streetlight`, `Water Leakage`, `Other` (damaged street furniture, guardrails).
* **Available Supply:** Over 7 million geographically referenced photos of UK infrastructure.
* **Label Reliability:** High photographic clarity with GPS coordinates.
* **Benchmark Overlap Risk:** Low (a small subset was harvested for benchmark water leakages). Mitigated by dHash distance check.

---

## 4. Controlled Acquisition Tooling Architecture

Acquisition is managed via [`scripts/datasets/controlled_expansion.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/scripts/datasets/controlled_expansion.py):

```
[Candidate Query Dispatch]
       │
       ├── Query API with Category Filter
       │
[Pre-Download Leakage Gate]
       │
       ├── Check upstream source_record_id in BenchmarkLeakageIndex?
       │        ├── MATCH: Skip immediately (0 bytes downloaded).
       │        └── CLEAN: Proceed to download image bytes.
       │
[Post-Download Validation Gate]
       │
       ├── Validate Magic Bytes (JPEG/PNG/WebP)
       ├── Decompression Bomb Defense (<= 25M px)
       ├── Compute SHA-256 and 64-bit dHash
       │
[Full Leakage & Duplicate Gate]
       │
       ├── Check exact SHA-256 against benchmark
       ├── Check 64-bit dHash Hamming distance <= 6 against 300 benchmark samples
       │        ├── LEAK DETECTED: Quarantine & Log.
       │        └── PASSED: Stage to datasets/raw/<source>/
       │
[Curation Pipeline Execution]
       │
       └── Run scripts/datasets/curate_training_dataset.py
```

### Strict Tooling Guardrails:
1. **Dry-Run by Default:** Requires `--execute` flag to execute network requests.
2. **Rate Limiting & Backoff:** Enforces a minimum 0.5s pause between downloads with exponential retry backoff (max 3 retries).
3. **No Direct Manifest Writing:** Acquisition tools only deposit raw files in `datasets/raw/<source>/`. Manifests, splits, and reports are generated exclusively by the curation pipeline.
4. **Zero Benchmark Contamination:** Every newly acquired candidate is evaluated against `datasets/benchmark_v1/` using cryptographic and perceptual hashing.

---

## 5. Quality Gates for Future Model Training

Before initiating transfer learning with MobileNetV3-Small, the following objective gates must be satisfied:

1. **Gate 1 — Clean Pool Size (Minimum Initial Gate):** Clean pool must contain at least **600 samples** ($\ge 100$ per class) with an 80/20 train/validation split.
2. **Gate 2 — Benchmark Isolation:** $0$ exact SHA-256 matches, $0$ source ID matches, and $0$ near-duplicates (dHash distance $\le 6$) in clean `train.jsonl` and `validation.jsonl`.
3. **Gate 3 — Group Disjunction:** Zero `group_id` overlap between train and validation splits ($\text{train\_groups} \cap \text{val\_groups} = \emptyset$).
4. **Gate 4 — Quarantine Isolation:** 100% of ambiguous, corrupted, or out-of-domain samples excluded from training partitions.
5. **Gate 5 — Verified Provenance:** 100% of samples must resolve to documented open licenses.
6. **Gate 6 — Benchmark Immutability:** Benchmark integrity hash `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b` must remain intact.
