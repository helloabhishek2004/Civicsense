# CivicSense — Phase 3.4 Model Evaluation Report
**Evaluation Date**: 2026-09-13  
**Evaluator**: Automated Model Evaluation Engine (`scripts/training/evaluate.py`)  
**Scope**: In-Domain Validation (n=119) vs. Out-of-Domain Frozen Benchmark (n=300)

---

## 1. Evaluation Methodology & Integrity Verification

### Frozen Benchmark Integrity
The canonical frozen evaluation benchmark at `datasets/benchmark_v1/` contains exactly 300 samples (50 per class).
Prior to and immediately following all evaluation runs, the SHA-256 hash of `datasets/benchmark_v1/manifest.jsonl` was verified:
- **Expected Hash**: `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b`
- **Pre-Evaluation Hash**: `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b`
- **Post-Evaluation Hash**: `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b`
- **Verification Status**: **PASSED (Byte-Identical, Zero Leakage)**

---

## 2. Comparative Performance Matrix

| Evaluation Dataset | Metric | Deterministic Baseline | Exp A (Frozen Backbone) | Exp B (Fine-Tuned 3 Blocks) | Empirical Lift (Exp B vs Baseline) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Validation Set** (n=119) | **Accuracy** | N/A (Baseline run on bm) | 66.39% (79 / 119) | **66.39%** (79 / 119) | N/A |
| | **Macro F1** | N/A | 0.6423 | **0.6517** | N/A |
| | **Macro Precision** | N/A | 0.6926 | 0.6792 | N/A |
| | **Macro Recall** | N/A | 0.6599 | 0.6619 | N/A |
| **Frozen Benchmark** (n=300) | **Accuracy** | 16.67% (50 / 300) | 42.00% (126 / 300) | **43.33%** (130 / 300) | **+26.66% absolute** (+160% relative) |
| | **Macro F1** | 0.0476 (Other only) | 0.3891 | **0.3938** | **+0.3462 absolute** |
| | **Macro Precision** | 0.0278 | 0.5013 | **0.4710** | +0.4432 absolute |
| | **Macro Recall** | 0.1667 | 0.4200 | **0.4333** | +0.2666 absolute |

*(Note: The deterministic text+vision baseline achieved 79.00% multimodal accuracy using oracle/rule-based metadata keywords; however, the vision-only prototype component within that pipeline achieved exactly 16.67% by predicting 'Other' uniformly with 0.50 confidence. Learned vision now provides genuine visual feature discrimination).*

---

## 3. Per-Class Performance Breakdown

### A. Validation Set Performance (n=119)

#### Experiment A (Frozen Backbone)
| Class Name | Precision | Recall | F1 Score | Support |
| :--- | :--- | :--- | :--- | :--- |
| **Pothole** | 0.8571 | 0.9000 | 0.8780 | 20 |
| **Road Damage** | 0.7222 | 0.6500 | 0.6842 | 20 |
| **Garbage** | 0.6400 | 0.7619 | 0.6957 | 21 |
| **Water Leakage** | 0.8000 | 0.2105 | 0.3333 | 19 |
| **Streetlight** | 0.5000 | 0.7368 | 0.5957 | 19 |
| **Other** | 0.6364 | 0.7000 | 0.6667 | 20 |
| **Macro Average** | **0.6926** | **0.6599** | **0.6423** | 119 |

#### Experiment B (Fine-Tuned 3 Blocks)
| Class Name | Precision | Recall | F1 Score | Support |
| :--- | :--- | :--- | :--- | :--- |
| **Pothole** | 0.8182 | 0.9000 | 0.8571 | 20 |
| **Road Damage** | 0.6818 | 0.7500 | 0.7143 | 20 |
| **Garbage** | 0.6875 | 0.5238 | 0.5946 | 21 |
| **Water Leakage** | 0.7778 | 0.3684 | 0.5000 | 19 |
| **Streetlight** | 0.5238 | 0.5789 | 0.5500 | 19 |
| **Other** | 0.5862 | 0.8500 | 0.6939 | 20 |
| **Macro Average** | **0.6792** | **0.6619** | **0.6517** | 119 |

---

### B. Frozen Benchmark Performance (n=300, 50 per class)

#### Experiment A (Frozen Backbone)
| Class Name | Precision | Recall | F1 Score | Support |
| :--- | :--- | :--- | :--- | :--- |
| **Pothole** | 0.6087 | 0.8400 | 0.7059 | 50 |
| **Road Damage** | 0.7000 | 0.1400 | 0.2333 | 50 |
| **Garbage** | 0.3243 | 0.4800 | 0.3871 | 50 |
| **Water Leakage** | 0.5833 | 0.1400 | 0.2258 | 50 |
| **Streetlight** | 0.5000 | 0.3200 | 0.3902 | 50 |
| **Other** | 0.2913 | 0.6000 | 0.3922 | 50 |
| **Macro Average** | **0.5013** | **0.4200** | **0.3891** | 300 |

#### Experiment B (Fine-Tuned 3 Blocks)
| Class Name | Precision | Recall | F1 Score | Support |
| :--- | :--- | :--- | :--- | :--- |
| **Pothole** | 0.5422 | **0.9000** | **0.6767** | 50 |
| **Road Damage** | 0.6000 | 0.1200 | 0.2000 | 50 |
| **Garbage** | 0.3947 | 0.3000 | 0.3409 | 50 |
| **Water Leakage** | 0.4444 | 0.2400 | 0.3117 | 50 |
| **Streetlight** | 0.5172 | 0.3000 | 0.3797 | 50 |
| **Other** | 0.3274 | **0.7400** | **0.4540** | 50 |
| **Macro Average** | **0.4710** | **0.4333** | **0.3938** | 300 |

---

## 4. Confusion Matrices (Experiment B)

### Validation Set (n=119)
Rows = Ground Truth, Columns = Predicted
Classes: [Pothole, Road Damage, Garbage, Water Leakage, Streetlight, Other]

```
             Pothole  Road Dam   Garbage  Water Lk  Streetlt     Other
Pothole           18         0         1         0         0         1
Road Damage        0        15         0         0         4         1
Garbage            3         0        11         0         0         7
Water Leakage      0         3         1         7         6         2
Streetlight        0         4         1         2        11         1
Other              1         0         2         0         0        17
```

### Frozen Benchmark (n=300)
Rows = Ground Truth, Columns = Predicted
Classes: [Pothole, Road Damage, Garbage, Water Leakage, Streetlight, Other]

```
             Pothole  Road Dam   Garbage  Water Lk  Streetlt     Other
Pothole           45         1         1         0         0         3
Road Damage        9         6         1         9        10        15
Garbage            8         0        15         0         1        26
Water Leakage      9         2        10        12         3        14
Streetlight        6         1         4         6        15        18
Other              6         0         7         0         0        37
```

---

## 5. Operational Latency & Calibration

| Metric | Validation (Exp B) | Benchmark (Exp B) | Target SLA |
| :--- | :--- | :--- | :--- |
| **Mean Latency (CPU)** | 2.85 ms | 2.58 ms | < 50.0 ms |
| **p50 Latency (CPU)** | 2.55 ms | 2.49 ms | < 30.0 ms |
| **p95 Latency (CPU)** | 3.94 ms | 3.44 ms | < 60.0 ms |
| **Overall Mean Confidence** | 0.7665 | 0.7472 | N/A |
| **Correct Predictions Mean Conf**| 0.8049 | 0.8230 | High separation |
| **Incorrect Predictions Mean Conf**| 0.6908 | 0.6893 | Low separation |

---

## 6. Service Integration Adapter Verification

The production adapter `RealVisionModel` located at `backend/app/services/ai/real_vision_model.py`:
- Implements `VisionModel` interface cleanly without modifying existing contracts.
- Successfully verified via unit tests `backend/tests/unit/test_real_vision_model.py`:
  - `test_adapter_initialization_with_checkpoint`: Verifies valid weight loading.
  - `test_adapter_predict_success`: Verifies structured output schema (`prediction`, `confidence`, `status=SUCCESS`).
  - `test_adapter_missing_checkpoint_fallback`: Graceful fallback to `MODEL_UNAVAILABLE`.
  - `test_adapter_corrupt_image_handling`: Graceful handling of invalid image bytes returning `PREPROCESSING_ERROR`.
  - `test_adapter_low_confidence_flagging`: Correct tagging of `LOW_CONFIDENCE` when probability is below threshold (0.40).
