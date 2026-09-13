# CivicSense Dataset Curation & Tooling Infrastructure

This directory contains standalone, reproducible Python tools for dataset acquisition, label normalization, image validation, deduplication, benchmark curation, and quality reporting.

## Architectural Principles

1. **Zero Heavy ML Dependencies**:
   - Strictly built using Python standard library and `Pillow` (`PIL.Image`).
   - Zero dependencies on `torch`, `torchvision`, `tensorflow`, `onnx`, `scikit-learn`, `pandas`, or `transformers`.
2. **Safety by Default (Dry-Run)**:
   - All network-capable scripts (`download_subsets.py`) default to dry-run mode. Real downloads require explicit `--execute`.
3. **No Fabricated Data or Synthetic Inflation**:
   - Shortages below target quotas (e.g. < 50 samples) are recorded transparently as shortages.
   - Scripts **never** duplicate, fabricate, or hallucinate samples to reach numerical targets.
4. **Decoupled Standalone Operation**:
   - Scripts can run without a live database or running FastAPI server.
   - When executing independently, tools dynamically resolve repository paths.

---

## Toolset Overview

### 1. `source_registry.py`
Candidate source dataset registry with metadata, verified licenses, target categories, URLs, and attribution requirements.
- **Sources**: `rdd2022` (Road Damage / Pothole), `taco` (Garbage), `boston311` (Streetlight / Water Leakage), `nyc311` (Water Leakage / Streetlight).
- **Functions**: `get_source(name)`, `list_sources()`, `get_sources_for_category(category)`.

### 2. `normalize_annotations.py`
Deterministic normalization engine mapping raw source labels to canonical CivicSense categories:
- **Canonical Categories**: `Pothole`, `Road Damage`, `Garbage`, `Water Leakage`, `Streetlight`, `Other`.
- **Mapping Outcomes**:
  - `ACCEPTED`: High-confidence mapping to canonical category with explicit rationale.
  - `REJECTED`: Out-of-scope, noise, or unmapped label (e.g., graffiti, noise complaints).
  - `MANUAL_REVIEW`: Ambiguous or composite label needing human triage.
- **CLI Usage**:
  ```bash
  python scripts/datasets/normalize_annotations.py --source rdd2022 --label D40
  ```

### 3. `validate_images.py`
Image validation and perceptual hashing tool ensuring security and quality:
- Path traversal protection (rejection of `..` or absolute paths outside root).
- File size limit (default 10 MB).
- Magic byte inspection (`JPEG`, `PNG`, `WEBP`).
- Pillow image decode with decompression bomb guard (`Image.MAX_IMAGE_PIXELS = 25_000_000`).
- Dimension bounds ($64 \le w, h \le 8192$ px).
- Cryptographic SHA-256 computation.
- 64-bit gradient difference hash (`dHash`) computed via fast luminance `tobytes()`.
- Quality heuristics: `is_blurry` (gradient energy threshold), `is_low_res` (< $224 \times 224$ px).
- **CLI Usage**:
  ```bash
  python scripts/datasets/validate_images.py path/to/image.jpg
  ```

### 4. `deduplicate_benchmark.py`
Two-phase deduplication engine:
1. **Exact Deduplication**: Grouping and filtering by cryptographic SHA-256 hash.
2. **Perceptual Near-Duplicate Deduplication**: Pairwise 64-bit dHash Hamming distance comparison ($\le 4$ bits threshold).
- Retains duplicate provenance records without destructive file deletion.
- **CLI Usage**:
  ```bash
  python scripts/datasets/deduplicate_benchmark.py --input-dir datasets/raw/rdd2022
  ```

### 5. `curate_benchmark.py`
Benchmark compilation pipeline orchestrating normalization, validation, deduplication, and `EvaluationSample` schema enforcement:
- Reads candidate sample records and images.
- Validates image integrity and extracts SHA-256 + dHash.
- Deduplicates samples while preserving provenance.
- Generates:
  - `datasets/benchmark_v1/benchmark_dataset.jsonl`
  - `datasets/benchmark_v1/manifest.json`
  - `datasets/benchmark_v1/curation_report.json`
- **CLI Usage**:
  ```bash
  python scripts/datasets/curate_benchmark.py --raw-dir datasets/raw --output-dir datasets/benchmark_v1 --target-per-category 50
  ```

### 6. `download_subsets.py`
Controlled dataset acquisition tool:
- Safe dry-run by default (`--dry-run`).
- Enforces sample limits (`--limit 50`), download size limits (`--max-bytes 50MB`), and request timeouts.
- Generates `datasets/raw/download_manifest.json`.
- **CLI Usage**:
  ```bash
  # Dry-run audit (safe, no downloads)
  python scripts/datasets/download_subsets.py --source rdd2022 --dry-run

  # Explicit download
  python scripts/datasets/download_subsets.py --source rdd2022 --execute --limit 50
  ```

### 7. `report_dataset.py`
Dataset balance, shortage, and quality analysis reporter:
- Analyzes sample counts per canonical category against target quotas (e.g. 50 samples).
- Flags shortages, zero-sample categories, and quality defects (blurry, low-res).
- Analyzes source and license distributions.
- Produces clean terminal summaries and writes `datasets/reports/dataset_report.json`.
- **CLI Usage**:
  ```bash
  python scripts/datasets/report_dataset.py --dataset-jsonl datasets/benchmark_v1/benchmark_dataset.jsonl --manifest datasets/benchmark_v1/manifest.json
  ```
