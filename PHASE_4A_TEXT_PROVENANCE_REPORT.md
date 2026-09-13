# CivicSense Phase 4A — Text Dataset Provenance and Leakage Audit Report

## Executive Summary

This audit rigorously inspects all **892 samples** across the CivicSense text intelligence corpus:
- **Training Split**: $n = 473$
- **Validation Split**: $n = 119$
- **Frozen Benchmark**: $n = 300$

### Key Linguistic & Provenance Findings
1. **Class Keyword Density**: **50.33% of frozen benchmark samples** contain explicit category keywords or synonyms, compared to **43.34% in training** and **49.58% in validation**.
2. **Metadata Label Discrepancy**: The frozen benchmark exhibits **36.0% metadata label leakage** (e.g., explicit 311 service codes or category names in captions), whereas validation has **43.7%**.
3. **Text Source Distribution**: Across all splits, samples span structured municipal labels, image captions, archive/catalog metadata, and citizen-like descriptions.
4. **Cross-Split Text Duplicates**: Detected **24 duplicate or near-duplicate texts** across distinct splits (details documented below).

---

## 1. Text Provenance Breakdown by Split

| Linguistic Source Category | Train ($n=473$) | Validation ($n=119$) | Benchmark ($n=300$) | Total ($n=892$) |
| :--- | :---: | :---: | :---: | :---: |
| **Archive/catalog description** | 142 (30.0%) | 28 (23.5%) | 9 (3.0%) | 179 (20.1%) |
| **Citizen-like description** | 112 (23.7%) | 35 (29.4%) | 117 (39.0%) | 264 (29.6%) |
| **Image caption** | 17 (3.6%) | 3 (2.5%) | 32 (10.7%) | 52 (5.8%) |
| **Other** | 40 (8.5%) | 13 (10.9%) | 42 (14.0%) | 95 (10.7%) |
| **Structured category label** | 162 (34.2%) | 40 (33.6%) | 100 (33.3%) | 302 (33.9%) |

---

## 2. Class Keyword Presence and Label Leakage Audit

| Split | Total Samples | Contains Class Keyword | Keyword-Free | Pct Keyword | Metadata Label Leakage | Mean Token Count |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Train** | 473 | 205 | 268 | 43.34% | 190 (40.17%) | 12.2 |
| **Validation** | 119 | 59 | 60 | 49.58% | 52 (43.7%) | 11.6 |
| **Benchmark** | 300 | 151 | 149 | 50.33% | 108 (36.0%) | 16.9 |

### Per-Class Keyword Breakdown (% samples with class keywords in text)

| Category | Train Support (Kw %) | Val Support (Kw %) | Benchmark Support (Kw %) |
| :--- | :---: | :---: | :---: |
| **Pothole** | 78 (100.0%) | 20 (100.0%) | 50 (100.0%) |
| **Road Damage** | 78 (34.62%) | 20 (40.0%) | 50 (32.0%) |
| **Garbage** | 84 (100.0%) | 21 (100.0%) | 50 (100.0%) |
| **Water Leakage** | 78 (15.38%) | 19 (21.05%) | 50 (22.0%) |
| **Streetlight** | 76 (5.26%) | 19 (31.58%) | 50 (48.0%) |
| **Other** | 79 (0.0%) | 20 (0.0%) | 50 (0.0%) |

---

## 3. Label Leakage & Cross-Split Collisions

### Cross-Split Text Overlap Findings
Detected **24 overlapping text phrases**:
- `[train_benchmark_collision]`: "mta new york city transit crews worked quickly to restore service on the a, c an"
- `[train_benchmark_collision]`: "poor conditions of property"
- `[train_benchmark_collision]`: "request for pothole repair"
- `[train_benchmark_collision]`: "road damage infrastructure defect photographed in public right-of-way"
- `[train_benchmark_collision]`: "illegal dumping"
- `[val_benchmark_collision]`: "poor conditions of property"
- `[val_benchmark_collision]`: "illegal dumping"
- `[val_benchmark_collision]`: "request for pothole repair"
- `[train_val_overlap]`: "publisher varies subjects: water-supply"
- `[train_val_overlap]`: "title varies slightly publisher and place of publication vary some vols. include"
- `[train_val_overlap]`: "request for pothole repair"
- `[train_val_overlap]`: "ca-r notes for ia: image may appear dark or faded due to the nature of microfilm"
- `[train_val_overlap]`: "vol. 1- prepared in the information division subjects: soil conservation united "
- `[train_val_overlap]`: "the metadata below describe the original scanning. follow the "all files: http" "
- `[train_val_overlap]`: "streetlight infrastructure defect, public right-of-way"
- *... and 9 additional minor overlaps.*

### Qualitative Forensic Risk Assessment
- **Benchmark Richness**: The benchmark possesses substantial keyword density (79.00% text accuracy on deterministic rules matches the exact keyword prevalence).
- **Validation Challenge**: The validation set has a significantly lower keyword proportion for classes like `Streetlight` and `Water Leakage` because Wikimedia archives describe catalog identifiers rather than defects.
- **Scientific Implication**: A semantic text model (MiniLM) will only add true value if it can classify **keyword-free** and **subtle descriptive** texts where keyword matching fails.

---

## 4. Text Quality Subgroup Definition for Phase 4A Evaluation

To rigorously evaluate semantic modeling vs. lexical pattern matching, all models in Phase 4A will be evaluated on the following stratified subgroups:
1. **All Benchmark Samples** ($n=300$)
2. **Keyword-Containing Subgroup** ($n=151$)
3. **Keyword-Free Subgroup** ($n=149$)
4. **Metadata-Rich Subgroup** ($n=100$)
5. **Citizen-like Description Subgroup** ($n=117$)

---
*Report generated automatically by `scripts/audit_text_provenance.py`.*