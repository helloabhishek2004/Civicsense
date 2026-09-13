# CivicSense — Phase 3.2 Step 3 Implementation Report
## Controlled Dataset Curation Infrastructure

**Date**: 2026-09-13  
**Status**: COMPLETE  
**Milestone**: Phase 3.2 — Step 3: Dataset Curation Pipeline  

---

## 1. Executive Summary

In Phase 3.2 Step 3, we built the complete, standalone dataset curation pipeline for CivicSense under `scripts/datasets/`. This infrastructure enables controlled acquisition, label normalization, defensive image validation, two-phase deduplication (cryptographic SHA-256 + perceptual 64-bit dHash), schema-validated benchmark assembly (`EvaluationSample`), dry-run downloading, and quality/balance reporting.

All work strictly adhered to the governance rules defined in `AGENTS.md`:
- **Zero Heavy ML Dependencies**: Standard library and `Pillow` only. No `torch`, `torchvision`, `tensorflow`, `scikit-learn`, `pandas`, `opencv`, or `transformers`.
- **Zero Model Weights / Training**: No neural networks were trained or downloaded.
- **Safety by Default**: All network-capable acquisition scripts default to dry-run mode (`--execute` required for physical downloads).
- **No Fabricated Data or Synthetic Padding**: The curation engine preserves actual real-world counts when categories fall below target quotas (e.g. < 50 samples). It strictly **never** fabricates synthetic images, duplicates existing samples, or maps unrelated labels to hit quotas.
- **Deduplication Provenance**: Exact duplicates and near-duplicates are flagged and cataloged without destructive deletion.
- **Honest Ground Truth State**: We do **not** claim the 300-sample physical benchmark is completed. The curation *tools* are verified and ready; physical execution of downloads will occur under controlled conditions.

---

## 2. Implemented Architecture & Tooling

```
scripts/
├── __init__.py                       # Package root marker
└── datasets/
    ├── __init__.py                   # Package exports
    ├── source_registry.py            # Dataset source metadata, licenses, and URLs
    ├── normalize_annotations.py      # Deterministic label normalization & audit taxonomy
    ├── validate_images.py            # Image file, dimensions, MIME, and dHash validator
    ├── deduplicate_benchmark.py      # Two-phase exact SHA-256 and near-duplicate dHash engine
    ├── curate_benchmark.py           # Benchmark compiler enforcing EvaluationSample schema
    ├── download_subsets.py           # Controlled subset downloader (dry-run default)
    ├── report_dataset.py             # Balance, shortage, and quality analysis reporter
    └── README.md                     # Detailed CLI and architectural documentation
```

### Component Details

#### 1. Source Registry (`scripts/datasets/source_registry.py`)
- Defines `DatasetSource` records for candidate datasets:
  - `rdd2022`: Road Damage Dataset 2022 (CC BY-SA 4.0).
  - `taco`: Trash Annotations in Context (CC BY-SA 4.0 / MIT).
  - `boston311`: City of Boston 311 Service Requests (Public Domain / ODC-ODbL).
  - `nyc311`: NYC OpenData 311 Service Requests (Public Domain / NYC Open Data Terms).
- Provides `get_source(name)`, `list_sources()`, and `get_sources_for_category(category)` functions with verified documentation and download URLs.

#### 2. Label Normalization Engine (`scripts/datasets/normalize_annotations.py`)
- Maps upstream source labels to canonical categories (`Pothole`, `Road Damage`, `Garbage`, `Water Leakage`, `Streetlight`, `Other`).
- Returns typed `NormalizationResult` with explicit `MappingOutcome`:
  - `ACCEPTED`: High-confidence canonical mapping with rationale.
  - `REJECTED`: Out-of-scope or noisy labels (e.g., graffiti, noise complaints).
  - `MANUAL_REVIEW`: Ambiguous or composite labels requiring human triage.
- Forbids silent or lossy mappings.

#### 3. Image Validator & Perceptual Hasher (`scripts/datasets/validate_images.py`)
- Path traversal defense (blocks `..` and escaped paths).
- File size boundary checks (enforces 10 MB limit).
- Magic byte verification for `JPEG` (`FF D8 FF`), `PNG` (`89 50 4E 47 0D 0A 1A 0A`), and `WEBP` (`RIFF....WEBP`).
- Pillow image decode with `MAX_IMAGE_PIXELS = 25_000_000` decompression bomb defense.
- Spatial dimension bounds: $64 \le \text{width}, \text{height} \le 8192$ px.
- Cryptographic SHA-256 computation over raw bytes.
- 64-bit gradient difference hash (`dHash`) computed via fast luminance `tobytes()` (avoiding Pillow 14 `getdata()` deprecation).
- Quality indicators: `is_blurry` (heuristic gradient energy threshold) and `is_low_res` ($< 224 \times 224$ px).

#### 4. Two-Phase Deduplication Engine (`scripts/datasets/deduplicate_benchmark.py`)
- **Phase 1 (Exact Deduplication)**: Cryptographic SHA-256 hash collision detection.
- **Phase 2 (Perceptual Near-Duplicate Deduplication)**: 64-bit dHash pairwise comparison with configurable Hamming distance threshold ($\le 4$ bits).
- Preserves full duplicate provenance (`original_sample_id`, `duplicate_sample_id`, `distance`, `sha256`) in audit logs without deleting physical files.

#### 5. Benchmark Curation Engine (`scripts/datasets/curate_benchmark.py`)
- Ingests raw sample manifests and image directories.
- Normalizes annotations and executes image validation.
- Runs two-phase deduplication.
- Preserves genuine shortages without synthetic padding or artificial inflation.
- Validates every record against Pydantic v2 `EvaluationSample`.
- Generates:
  - `datasets/benchmark_v1/benchmark_dataset.jsonl`
  - `datasets/benchmark_v1/manifest.json`
  - `datasets/benchmark_v1/curation_report.json`

#### 6. Controlled Downloader (`scripts/datasets/download_subsets.py`)
- Safe by default: runs in dry-run mode unless `--execute` is explicitly passed.
- Limits sample counts (`--limit 50`) and download bandwidth (`--max-bytes 50MB`).
- Generates `datasets/raw/download_manifest.json` recording sample targets, download sizes, and SHA-256 checksums.

#### 7. Quality & Balance Reporter (`scripts/datasets/report_dataset.py`)
- Inspects curated JSONL files against canonical target quotas (50 samples per class).
- Highlights class shortages, zero-sample gaps, and image quality warnings (`is_blurry`, `is_low_res`).
- Summarizes source and license breakdowns.
- Writes structured JSON reports to `datasets/reports/dataset_report.json`.
- Strictly does **not** evaluate model predictions (preventing metric fabrication at curation time).

---

## 3. Verification & Validation Summary

| Check | Tool / Command | Result |
| :--- | :--- | :--- |
| **Unit Tests** | `pytest tests/unit/test_dataset_tooling.py -v` | **11 / 11 Passed** (0.16s) |
| **Full Test Suite** | `pytest tests/` | **118 / 118 Passed** (3.10s) |
| **Linting & Formatting** | `ruff check . ../scripts/datasets` | **0 Errors** (All clean) |
| **Strict Type Checking** | `mypy ../scripts/datasets app tests` | **0 Issues** across 111 source files |
| **Dry-Run Acquisition** | `python scripts/datasets/download_subsets.py --source rdd2022 --dry-run` | Verified `datasets/raw/download_manifest.json` |

### New Automated Unit Tests (`tests/unit/test_dataset_tooling.py`)
1. `test_source_registry_lookup_and_fields`: Verifies all registered sources have licenses, URLs, and attribution.
2. `test_canonical_mapping_accepted_labels`: Validates exact canonical category mappings (`Pothole`, `Road Damage`, `Garbage`, etc.).
3. `test_unknown_and_ambiguous_label_rejection`: Confirms out-of-scope labels are rejected or routed to manual review.
4. `test_image_validation_valid_jpeg`: Verifies valid image decoding, dimensions, SHA-256, and 16-char hex dHash.
5. `test_image_validation_corrupt_and_missing`: Tests that truncated bytes or nonexistent files are rejected gracefully.
6. `test_image_validation_path_traversal`: Ensures directory traversal attempts (`../../etc/passwd`) raise security exceptions.
7. `test_exact_duplicate_detection`: Validates exact SHA-256 collision detection.
8. `test_near_duplicate_detection_dhash`: Validates perceptual near-duplicate filtering within Hamming distance $\le 4$.
9. `test_curate_benchmark_shortage_preservation_and_no_fabrication`: Verifies category counts below target (e.g. 2 samples) are preserved without synthetic inflation.
10. `test_download_subsets_dry_run`: Verifies download tool executes safely without network access in dry-run mode.
11. `test_report_dataset_generation`: Verifies balance and shortage reporting produces expected JSON metrics.

---

## 4. Documentation & Memory Parity

- **`datasets/README.md`**: Updated with data governance rules, metadata fields, directory layout, and licensing restrictions.
- **`scripts/datasets/README.md`**: Updated with complete script documentation, CLI usage examples, and architectural principles.
- **`memory.md`**:
  - Section 8 (`MLOps & Evaluation Benchmark`) updated with Step 3 curation infrastructure details.
  - Section 9 (`Major Architectural Changes`) updated with Phase 3.2 Step 3 record.
  - Section 10 (`Current Implementation State`) updated to 118 passing tests and 111 Mypy-verified source files.

---

## 5. Next Steps

With the curation tools fully implemented and verified, the next recommended phase is **Phase 3.2 Step 4: Controlled Sample Download & Baseline Evaluation**:
1. Execute controlled physical downloads of small sample subsets (target: up to 50 samples per category from RDD2022, TACO, Boston 311, and NYC 311).
2. Curate the official `benchmark_v1` dataset using `curate_benchmark.py`.
3. Run `BenchmarkRunner` with `OfflineDeterministicEvaluator` against the curated dataset to establish authentic baseline performance metrics.
