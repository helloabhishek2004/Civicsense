# CivicSense — AI Methodology & Evaluation

**Version:** 1.0.0
**Last Updated:** 2026-09-13

---

## 1. Text Embedding Model

| Property | Value |
|---|---|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Parameters | 22.7 million |
| Embedding Dimension | 384 |
| Framework | PyTorch + sentence-transformers |
| Quantization | FP32 (90.87 MB); INT8 estimate ~22.7 MB |

### Why This Model
- Lightweight enough for server-side real-time inference (~10ms per report)
- Strong semantic similarity on short text (citizen descriptions are typically 1–3 sentences)
- Well-established benchmark performance on semantic textual similarity tasks
- No GPU required for inference

---

## 2. Text Similarity Approach

1. **Preprocessing:** Strip EXIF, normalize Unicode, lowercase
2. **Encoding:** Attention-mask-aware mean pooling over token embeddings
3. **Normalization:** L2 unit-norm projection
4. **Similarity:** Cosine similarity between report embedding and issue centroid embedding

### Embedding Storage
- Stored as JSON arrays in `reports.text_embedding` and `issues.text_embedding` columns
- Model version recorded in `embedding_model_version` for provenance

---

## 3. Spatial Constraints

| Parameter | Value | Notes |
|---|---|---|
| Distance metric | Haversine | Great-circle distance on WGS84 |
| Radius threshold | 50 meters | Reports beyond 50m get spatial score = 0 |
| Distance scoring | Linear decay within radius | 0m → 1.0, 50m → 0.0 |
| Null Island defense | (0, 0) rejected | Prevents GPS-failed reports from clustering |

---

## 4. Category Compatibility

| Score | Meaning |
|---|---|
| 1.0 (Exact) | Same explicit category |
| 0.5 (Bridge) | Related categories (configurable pairs) |
| 0.0 (Mismatch) | Different categories |

**Critical safety gate:** When both report and issue have explicit non-`Other` categories that differ, the action is forced to `NEW_ISSUE` regardless of text/spatial proximity.

---

## 5. Match Decision Thresholds

| Threshold | Score Range | Action |
|---|---|---|
| High confidence | ≥ 0.70 | `AUTO_LINK` — automatic issue linkage |
| Candidate | 0.45 – 0.70 | `CANDIDATE` — human review required |
| No match | < 0.45 | `NEW_ISSUE` — create new issue |

### Weight Configuration
```
SIMILARITY_TEXT_WEIGHT = 0.40
SIMILARITY_DISTANCE_WEIGHT = 0.35
SIMILARITY_CATEGORY_WEIGHT = 0.25
```

---

## 6. Human-in-the-Loop Design

The system is explicitly **decision-support, not autonomous authority**.

- **CANDIDATE matches** (45%–70% confidence) are routed to human municipal officers
- Officers can **Approve** (confirm linkage) or **Reject** (keep independent)
- Officers can **Reject and relink** to an alternate issue
- All decisions are audit-logged with reviewer identity, notes, and timestamps
- Already-reviewed matches return 409 `MATCH_ALREADY_REVIEWED`

---

## 7. Priority Scoring

| Factor | Weight | Description |
|---|---|---|
| Severity | 0.30 | Physical risk of the defect (keyword heuristic) |
| Report volume | 0.25 | Number of reports linked to issue (saturation curve) |
| Unique reporters | 0.20 | Distinct citizens reporting (public impact) |
| Recency | 0.15 | Time since most recent report (exponential decay) |
| Persistence | 0.10 | Days since issue creation (ongoing problems score higher) |

**Output:** Weighted sum → 0–100 score → mapped to PriorityLevel via configurable thresholds:
- CRITICAL ≥ 65
- HIGH ≥ 40
- MEDIUM ≥ 15
- LOW < 15

**Note:** These weights are provisional heuristics, not scientifically validated.

---

## 8. Synthetic Evaluation Dataset

| Property | Value |
|---|---|
| Benchmark samples | 300 |
| Unique incident groups | 300 (no cross-split leakage) |
| Categories | 6 (Pothole, Road Damage, Garbage, Water Leakage, Streetlight, Other) |
| Integrity hash | `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b` |

### Duplicate Evaluation (Synthetic)
| Metric | Value | Notes |
|---|---|---|
| Precision | 100.0% | Zero false merges |
| Recall | 100.0% | Zero missed duplicates |
| F1 Score | 1.0000 | Perfect on synthetic pairs |
| Candidate rate | 35.0% | Safely deferred to human review |

**Important:** These metrics apply to the current synthetic benchmark only. They do not represent real-world accuracy.

---

## 9. Known Weaknesses

1. **Severity is keyword-heuristic:** Based on words like "danger", "emergency", "school" — not ML-classified
2. **GPS jitter:** Reports within 50m are considered spatially co-located; real-world GPS accuracy varies
3. **Text-only analysis:** No image classification is currently integrated into the similarity pipeline
4. **Synthetic-only evaluation:** All metrics are on manufactured data, not real civic reports
5. **Category bridge mapping:** Limited to predefined related-category pairs
6. **No temporal clustering:** Does not consider time-of-day or seasonal patterns

---

## 10. Evaluation Scripts

| Script | Purpose |
|---|---|
| `scripts/evaluate_ai_pipeline.py` | End-to-end duplicate matching precision/recall |
| `scripts/evaluate_baseline.py` | Text-only classification baseline |
| `scripts/evaluate_multimodal_fusion.py` | Multimodal fusion comparison |
| `scripts/evaluate_semantic_text.py` | MiniLM text model evaluation |
| `scripts/audit_latency_profile.py` | Pipeline latency measurement |
| `scripts/audit_duplicate_sensitivity.py` | Cross-split text overlap analysis |

---

## 11. Statistical Validation

- **McNemar's paired test** (MiniLM vs deterministic baseline): p = 0.0001 (statistically significant)
- **Bootstrap confidence intervals** (10,000 resamples): Accuracy difference 95% CI [+4.33pp, +12.33pp]
- **Temperature scaling:** Optimal T* = 0.50, reducing Brier score by 20.5%

---

## 12. Decision-Support Disclaimer

> CivicSense AI outputs are **probabilistic suggestions**, not ground truth.
> All candidate matches require human municipal officer review before action.
> The system is designed to assist triage officers, not replace their judgment.
> No automated dispatch occurs without human confirmation.
