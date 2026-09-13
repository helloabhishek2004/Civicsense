# CivicSense — Phase 3.2 Step 2 Implementation Report
## Evaluation Infrastructure Scaffolding

**Date:** September 12, 2026  
**Status:** Completed  
**Repository State:** Zero regressions (107 passing backend tests, 0 Ruff errors, 0 Mypy issues across 102 source files)

---

## 1. Executive Summary

In accordance with the Phase 3.2 roadmap and the findings from the Phase 3.2 Step 1 Repository Audit, this step established the foundational evaluation and dataset infrastructure for CivicSense.

### Core Objectives Achieved
1. **Isolated Dataset Storage Hierarchy**: Created `datasets/` (`raw/`, `benchmark_v1/images/`) and `scripts/datasets/` with strict `.gitignore` rules preventing binary image/archive bloat while tracking canonical metadata (`benchmark_dataset.jsonl`, `manifest.json`).
2. **Canonical Benchmark Schemas (`backend/app/evaluation/schema.py`)**: Built Pydantic v2 schemas (`EvaluationSample`, `BoundingBox`, `BenchmarkManifest`, `EvaluationResultRecord`, `BenchmarkSplit`) enforcing strict validation against the authoritative 6-category taxonomy from `PredictionNormalizer.CATEGORY_LABELS`.
3. **Offline Headless Evaluator (`backend/app/evaluation/evaluator.py`)**: Built `OfflineDeterministicEvaluator`, wrapping the hardened Phase 2 deterministic AI sub-services (`InputValidator`, `PrototypeVisionAnalyzer`, `PrototypeTextPatternAnalyzer`, `PrototypeFusionEngine`, `PrototypeDecisionEngine`, `PredictionNormalizer`). Executes 100% offline in-memory without FastAPI, PostgreSQL, or network connections.
4. **Pure Python Evaluation Metrics Suite (`backend/app/evaluation/metrics.py`)**: Implemented zero-dependency calculations for overall accuracy, macro F1/precision/recall, balanced accuracy, per-class metrics with support, a 6x6 confusion matrix with deterministic label ordering, human-review abstention rate, selective accuracy on accepted predictions, and p50/p95/p99 latency percentiles.
5. **Headless Benchmark Runner (`backend/app/evaluation/runner.py`)**: Built `BenchmarkRunner` to stream and evaluate JSONL benchmark datasets, load local images, record execution timing, and compute aggregate metrics.
6. **Automated Verification Suite (`backend/tests/unit/test_evaluation.py`)**: Created 19 comprehensive unit tests covering schema validation, rejection of unmapped classes, coordinate validation, zero-input edge cases, confusion matrix layout, abstention rate math, percentile latency calculation, corrupted line handling, and offline execution across all modalities.

---

## 2. Directory Structure Created

```
CivicSense/
├── datasets/
│   ├── .gitignore                  # Ignores raw/ and benchmark_v1/images/, tracks metadata JSONL & manifest
│   ├── README.md                   # Dataset provenance, schema contracts, and licensing rules
│   ├── raw/                        # Transient/ignored directory for raw upstream downloads
│   └── benchmark_v1/
│       └── images/                 # Local image repository for validated benchmark images (gitignored)
├── scripts/
│   └── datasets/
│       └── README.md               # Script authoring conventions and zero-heavy-dependency rules
└── backend/
    ├── app/
    │   └── evaluation/
    │       ├── __init__.py         # Public evaluation package exports
    │       ├── schema.py           # Pydantic v2 data contracts for evaluation
    │       ├── evaluator.py        # OfflineDeterministicEvaluator
    │       ├── metrics.py          # Zero-dependency classification & latency metrics
    │       └── runner.py           # Headless benchmark execution engine
    └── tests/
        └── unit/
            └── test_evaluation.py  # 19 automated unit tests
```

---

## 3. Implementation Details

### 3.1. Canonical Schemas (`app/evaluation/schema.py`)
- **`BenchmarkSplit`**: Enum with `train`, `val`, `test`, `benchmark`.
- **`BoundingBox`**: Spatial model requiring normalized $[0.0, 1.0]$ coordinates and validating that $x_{\min} \le x_{\max}$ and $y_{\min} \le y_{\max}$.
- **`EvaluationSample`**: Dataset-agnostic canonical sample format. Includes fields for `sample_id`, `image_rel_path`, `source_dataset`, `source_record_id`, `canonical_category`, `original_category`, `bounding_boxes`, `text_description`, `split`, `license`, `license_url`, `attribution`, `sha256`, `phash`, `review_status`, and `metadata_json`.
  - Enforces strict validation: `canonical_category` must be one of `"Pothole"`, `"Road Damage"`, `"Garbage"`, `"Water Leakage"`, `"Streetlight"`, or `"Other"`. Any unmapped or non-canonical label is rejected with a `ValueError`.
- **`BenchmarkManifest`**: Metadata schema capturing `benchmark_version`, `total_sample_count`, `category_counts`, `source_dataset_counts`, and integrity hashes.
- **`EvaluationResultRecord`**: Output model recording sample ID, ground truth, prediction, confidence tier, review required flag, latency in ms, and whether the prediction was correct.

### 3.2. Offline Evaluator (`app/evaluation/evaluator.py`)
- Instantiates deterministic AI pipeline sub-services once at initialization:
  - `InputValidator`
  - `PrototypeVisionAnalyzer`
  - `PrototypeTextPatternAnalyzer`
  - `PrototypeFusionEngine`
  - `PrototypeDecisionEngine`
  - `PredictionNormalizer`
- Implements `_OfflineEvidenceAdapter`, a lightweight in-memory dataclass mimicking `Evidence` without requiring database rows or network storage.
- Sub-millisecond timing instrumentation using `time.perf_counter()` captures exact vision, text, fusion, and decision latencies.
- Supports 4 distinct evaluation modes:
  1. **Multimodal**: Valid image bytes + text description.
  2. **Vision-Only**: Image bytes present, text absent (`text=None`).
  3. **Text-Only**: Image absent (`image_bytes=None`), text description present.
  4. **Fallback**: Both modalities absent or invalid; falls back to `"Other"` with 0.35 confidence and `requires_review=True`.

### 3.3. Pure Python Metric Suite (`app/evaluation/metrics.py`)
- **Zero Heavy Dependencies**: Implemented strictly using Python's standard library (`math`). No `scikit-learn`, `numpy`, or `scipy`.
- **Classification Metrics**:
  - Overall Accuracy: $\frac{\text{correct}}{\text{total}}$
  - Macro Precision, Recall, and F1 (averaged across classes with non-zero support).
  - Balanced Accuracy: Macro average of per-class recall.
  - Per-Class Metrics: Precision, Recall, F1, and Support for all canonical classes.
  - Deterministic 2D Confusion Matrix: Rows represent true classes, columns represent predicted classes, with label ordering strictly defined by `PredictionNormalizer.CATEGORY_LABELS`.
  - Abstention Rate: Fraction of samples flagged with `review_required=True`.
  - Selective Accuracy: Accuracy evaluated strictly over the non-abstained (accepted) subset.
- **Telemetry Metrics**:
  - Percentiles ($p_{50}$, $p_{95}$, $p_{99}$) computed via linear interpolation.

### 3.4. Headless Benchmark Runner (`app/evaluation/runner.py`)
- Streams `benchmark_dataset.jsonl` line-by-line to prevent high memory usage.
- Validates each JSON record against `EvaluationSample`.
- Resolves local image files relative to `benchmark_root`.
- Executes `OfflineDeterministicEvaluator` and records latency and classification decisions.
- Aggregates metrics and returns a structured evaluation report dictionary.

---

## 4. Verification & Testing

### 4.1. Unit Test Suite (`backend/tests/unit/test_evaluation.py`)
All 19 automated tests passed in 0.11 seconds:
1. `test_evaluation_sample_valid`: Valid sample instantiation and field retention.
2. `test_evaluation_sample_invalid_canonical_category_rejected`: Non-canonical labels (`"Trash"`, `"Sinkhole"`) rejected.
3. `test_bounding_box_coordinates_validation`: Inverted coordinates ($x_{\max} < x_{\min}$) and out-of-bound coordinates rejected.
4. `test_benchmark_manifest_validation`: Manifest counts and schema version validated.
5. `test_evaluation_result_record_validation`: Result record serialization verified.
6. `test_metrics_empty_inputs`: Graceful zero returns on empty datasets without exceptions.
7. `test_metrics_perfect_predictions`: Precision, recall, and F1 equal 1.0 when predictions match ground truth.
8. `test_metrics_completely_incorrect_predictions`: Zero accuracy and F1 when all predictions mismatch.
9. `test_metrics_missing_classes`: Safe handling when dataset contains only a subset of canonical classes (no `KeyError` or division by zero).
10. `test_metrics_confusion_matrix_ordering`: Deterministic canonical category class ordering verified.
11. `test_metrics_abstention_and_selective_accuracy`: Abstention rate and selective accuracy calculations verified.
12. `test_latency_percentile_calculation`: $p_{50}$, $p_{95}$, and $p_{99}$ latency calculations verified.
13. `test_offline_evaluator_multimodal_execution`: Offline evaluation with image bytes and text.
14. `test_offline_evaluator_vision_only_execution`: Offline evaluation with image bytes only.
15. `test_offline_evaluator_text_only_execution`: Offline evaluation with text only.
16. `test_offline_evaluator_empty_fallback`: Offline fallback to `"Other"` and low severity.
17. `test_benchmark_runner_missing_file_raises`: `FileNotFoundError` when dataset file is missing.
18. `test_benchmark_runner_malformed_json_raises`: `ValueError` with line number on malformed JSONL.
19. `test_benchmark_runner_execution_with_dataset`: End-to-end headless run over synthetic JSONL with image files.

### 4.2. Full Test Suite & Static Analysis
- **Pytest**: `107 passed, 14 warnings in 2.51s` (88 existing + 19 new evaluation tests).
- **Ruff**: `All checks passed!` across the entire backend repository.
- **Mypy**: `Success: no issues found in 102 source files` with strict Pydantic plugin enabled.

---

## 5. Non-Negotiable Invariants Compliance

| Invariant | Status | Evidence |
| :--- | :--- | :--- |
| **Zero Model Weights Downloaded** | Preserved | No weights or model files were downloaded or checked in. |
| **Zero Heavy Dependencies Added** | Preserved | `pyproject.toml` untouched; pure standard library used for metrics and runner. |
| **Zero Production Schema Changes** | Preserved | No Alembic migrations or SQLAlchemy models touched. |
| **Decoupled Architecture** | Preserved | `app/evaluation/` does not import or depend on database sessions, routes, or HTTP clients. |
| **Deterministic AI Unchanged** | Preserved | Existing production services (`input_validator.py`, `vision_analyzer.py`, `decision_engine.py`) unmodified. |

---

## 6. Next Steps: Phase 3.2 Step 3 (Curation Scripts)

With the evaluation infrastructure now in place, the project is ready for **Phase 3.2 Step 3**:
1. Create isolated download and curation scripts in `scripts/datasets/`:
   - `download_subsets.py`: Controlled, subsetted downloads of RDD2022, TACO, and Boston 311.
   - `curate_benchmark.py`: Normalizing source annotations into canonical CivicSense categories and generating `benchmark_dataset.jsonl`.
   - `deduplicate_benchmark.py`: Exact SHA-256 and perceptual hash (pHash) near-duplicate elimination.
2. Build the 300-sample balanced mini-benchmark (50 samples per canonical category).
3. Execute `BenchmarkRunner` with `OfflineDeterministicEvaluator` to generate baseline metrics on actual civic data.
