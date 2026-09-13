# CivicSense Training Dataset (training_v1)

**Version:** 1.0.0
**Generated:** 2026-09-13T07:33:35.203061+00:00
**Status:** Curated Foundation Pool (Zero Benchmark Leakage)

## Overview
- **Total Registered Samples:** 995
- **Clean Training Set (`splits/train.jsonl`):** 473
- **Clean Validation Set (`splits/validation.jsonl`):** 119
- **Quarantined Samples (`splits/quarantine.jsonl`):** 403
- **Benchmark Leakage Rejections:** 305 (100% quarantined)

## Directory Structure
```
datasets/training_v1/
├── README.md                     # Dataset documentation
├── manifest.jsonl                # Master manifest containing all records
├── dataset_summary.json          # Dataset metadata and aggregated distributions
├── splits/
│   ├── train.jsonl               # Clean training split (group isolated)
│   ├── validation.jsonl          # Clean validation split (group isolated)
│   └── quarantine.jsonl          # Quarantined / ambiguous / leaked samples
├── reports/
│   ├── curation_report.json      # Pipeline execution summary
│   ├── leakage_report.json       # Benchmark leakage verification details
│   ├── duplicate_report.json     # Intra-dataset duplicates and near-duplicates
│   ├── quality_report.json       # Image decodability, dimensions, quality flags
│   ├── class_distribution.json   # Category breakdown per split
│   └── source_distribution.json  # Source breakdown per split
└── provenance/
    └── source_registry.json      # License, redistribution, and legal provenance
```

## Governance Invariants
1. **Benchmark Isolation**: No sample in `train.jsonl` or `validation.jsonl` collides with `datasets/benchmark_v1/` by SHA-256, Source ID, URL, or 64-bit dHash (\le 6 bits).
2. **Group-Level Isolation**: No `group_id` spans across both train and validation splits.
3. **Quarantine Policy**: Ambiguous and leakage-detected records are quarantined and excluded from training.
