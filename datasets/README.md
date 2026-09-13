# CivicSense Datasets Repository

This directory manages dataset curation, provenance metadata, and offline evaluation benchmarks for CivicSense.

## Policy & Governance

1. **Zero Raw Heavy Data in Git**:
   - Upstream raw datasets (`datasets/raw/`) and benchmark image payloads (`datasets/benchmark_v1/images/`) are git-ignored.
   - Only lightweight schema metadata (`benchmark_dataset.jsonl`, `manifest.json`, `splits.json`, `curation_report.json`, `dataset_report.json`, `README.md`) is tracked in version control.

2. **Strict Provenance Tracking**:
   Every sample record in `benchmark_dataset.jsonl` must preserve:
   - `sample_id`: Unique deterministic identifier (e.g., `sample_000001`).
   - `source_dataset`: Upstream source (`rdd2022`, `taco`, `boston311`, `nyc311`).
   - `source_record_id`: Upstream record or filename identifier.
   - `canonical_category`: Normalized CivicSense category (`Pothole`, `Road Damage`, `Garbage`, `Water Leakage`, `Streetlight`, `Other`).
   - `original_category`: Raw source label (e.g., `D40`, `Plastics`, `Street Light Outages`).
   - `license`: Explicit upstream license name (e.g., `CC BY-SA 4.0`, `CC BY 4.0`, `Public Domain / ODC-ODbL`).
   - `license_url`: Official license URL.
   - `attribution`: Author/institution attribution string.
   - `sha256`: Cryptographic payload integrity hash.
   - `phash`: Perceptual difference hash (64-bit dHash hex) for near-duplicate and leakage defense.
   - `review_status`: Curation verification state (`CONFIRMED`, `DISPUTED`, `EXCLUDED`).

3. **No Synthetic Padding & Shortage Preservation**:
   - If a category has fewer than 50 real-world samples, the curation engine preserves the exact real count and logs the deficit.
   - It strictly **never** fabricates synthetic images, duplicates existing samples, or maps unrelated labels to hit target quotas.

4. **Legal & Licensing Compliance**:
   - All source datasets must have permissive or compatible open licenses.
   - Benchmark splits are intended strictly for controlled evaluation and verification.

## Directory Layout

```
datasets/
├── raw/                      # Ephemeral directory for downloaded upstream raw archives (git-ignored)
│   ├── download_manifest.json# Manifest tracking downloaded files, bytes, and sha256 checksums
│   ├── rdd2022/              # Raw RDD2022 image subset and XML annotations
│   ├── taco/                 # Raw TACO image subset and annotations.json
│   ├── boston311/            # Raw Boston 311 image subset and CSV/JSON records
│   └── nyc311/               # Raw NYC 311 image subset and CSV/JSON records
├── benchmark_v1/             # Curated benchmark dataset
│   ├── images/               # Standardized evaluation images named by sample_id/sha256 (git-ignored)
│   ├── benchmark_dataset.jsonl # Line-delimited canonical sample metadata
│   ├── manifest.json         # Benchmark checksums, category distributions, and generation metadata
│   └── curation_report.json  # Audit log of ingested, accepted, rejected, and duplicate samples
└── reports/                  # Generated dataset quality and distribution reports
    └── dataset_report.json   # Quality, balance, and shortage analysis report
```
