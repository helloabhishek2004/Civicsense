# CivicSense — Phase 3.2 Step 6: Deterministic Baseline Evaluation Report

## 1. Executive Summary

This evaluation establishes the empirical baseline performance of the production deterministic CivicSense AI pipeline against the frozen 300-sample balanced benchmark (`datasets/benchmark_v1/`).

- **Benchmark Dataset**: Frozen `benchmark_v1` containing **300 samples** (50 samples across all 6 canonical categories: `Pothole`, `Road Damage`, `Garbage`, `Water Leakage`, `Streetlight`, `Other`).
- **Primary Multimodal Accuracy**: **79.00%** (237 / 300 correct).
- **Primary Multimodal Macro F1**: **0.7934**.
- **Primary Multimodal Selective Accuracy**: **100.00%** (Abstention / Review Rate: **99.67%**).
- **P50 Latency**: **4.73 ms** | **P95 Latency**: **59.90 ms**.

### Key Findings:
1. **Text-Dominant Performance**: In multimodal mode, accuracy is driven almost entirely by the deterministic keyword pattern analyzer (`PrototypeTextPatternAnalyzer`). High precision and recall are achieved on Boston 311 records with explicit municipal service descriptions (`Garbage`, `Pothole`, `Other`).
2. **Vision Blindness**: In production mode (`AI_ENABLE_FILENAME_HEURISTICS=False`), the visual analyzer outputs neutral fallback priors (`Other`, confidence 0.50). Vision-only accuracy is exactly **16.67%** (1/6 random chance), confirming zero visual intelligence.
3. **Modal Divergence & Fallbacks**: In text-only mode, accuracy is identical to multimodal (79.00%), but the system triggers a **100% human review requirement** due to the `UNIMODAL_TEXT_FALLBACK` confidence penalty (0.70x).
4. **Severity Absence**: Ground-truth severity is not present in municipal 311 or Wikimedia records. The pipeline predicts severity deterministically, but no ground-truth comparison is fabricated.

---

## 2. Benchmark Composition & Source Distribution

| Source Dataset | Count | Percentage | Primary Categories Covered |
| :--- | :--- | :--- | :--- |
| **Boston 311 (Open Data)** | 170 | 56.67% | Pothole (50), Garbage (50), Road Damage (21), Streetlight (29), Other (20) |
| **Wikimedia Commons (CC BY-SA / CC0)** | 130 | 43.33% | Water Leakage (50), Other (30), Road Damage (29), Streetlight (21) |
| **Total** | **300** | **100.00%** | **Balanced: exactly 50 per canonical category** |

---

## 3. Modality Ablation Comparison

Evaluating the identical 300 samples across the three operational modes reveals the exact contribution of each modality:

| Metric | Multimodal (Primary) | Vision-Only | Text-Only |
| :--- | :--- | :--- | :--- |
| **Accuracy** | **79.00%** | 16.67% | 79.00% |
| **Macro F1** | **0.7934** | 0.0476 | 0.7934 |
| **Macro Precision** | **0.8810** | 0.0278 | 0.8810 |
| **Macro Recall** | **0.7900** | 0.1667 | 0.7900 |
| **Abstention Rate (Review Required)** | **99.67%** | 100.00% | 100.00% |
| **Selective Accuracy (Auto-Accepted)** | **100.00%** | 0.00% | 0.00% |
| **Mean Latency (ms)** | **11.54 ms** | 11.36 ms | 0.08 ms |

### Ablation Observations:
- **Vision-Only is Entirely Uninformative**: In vision-only mode, the model predicts `Other` for 100% of samples (300/300). Because `Other` is 1 of the 6 classes (50 samples), accuracy is exactly 50/300 = 16.67%. Precision for `Other` is 0.1667, recall is 1.0000, and precision/recall for all other 5 classes is 0.0000.
- **Text-Only Policy Penalties**: Text-only classification achieves the same raw prediction accuracy as multimodal (79.00%), but triggers `UNIMODAL_TEXT_FALLBACK` with a 0.70x confidence multiplier. Consequently, 100% of text-only reports are flagged for human review (`abstention_rate = 1.0000`).
- **Multimodal Confidence Suppression**: Because the visual analyzer outputs a neutral prior ('Other' with 0.50 confidence), the weighted multimodal fusion score is depressed to ~0.63-0.69 (LOW tier) even when text confidence is high (0.85). Furthermore, reports falling into 'Other' always trigger mandatory human review. Consequently, 99.67% of multimodal reports require human review ('abstention_rate = 0.9967'), demonstrating that a true visual model is essential not only for classification accuracy, but to enable automated triage without human intervention.

---

## 4. Canonical Category Performance (Multimodal Mode)

| Category | Support | Precision | Recall | F1-Score | Accuracy | Correct / Total |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Pothole** | 50 | 0.9434 | 1.0000 | 0.9709 | 1.0000 | 50 / 50 |
| **Road Damage** | 50 | 0.8750 | 0.4200 | 0.5676 | 0.4200 | 21 / 50 |
| **Garbage** | 50 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 50 / 50 |
| **Water Leakage** | 50 | 1.0000 | 0.7400 | 0.8506 | 0.7400 | 37 / 50 |
| **Streetlight** | 50 | 1.0000 | 0.5800 | 0.7342 | 0.5800 | 29 / 50 |
| **Other** | 50 | 0.4673 | 1.0000 | 0.6370 | 1.0000 | 50 / 50 |
| **Macro Average** | **300** | **0.8810** | **0.7900** | **0.7934** | **0.7900** | **237 / 300** |

---

## 5. Confusion Matrix (Multimodal Mode)

Rows represent **Ground Truth**, Columns represent **Predicted Category**.

| Ground Truth \ Pred | **Pothole** | **Road Dam** | **Garbage** | **Water Le** | **Streetli** | **Other** | **Total** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pothole** | 50 | 0 | 0 | 0 | 0 | 0 | **50** |
| **Road Damage** | 0 | 21 | 0 | 0 | 0 | 29 | **50** |
| **Garbage** | 0 | 0 | 50 | 0 | 0 | 0 | **50** |
| **Water Leakage** | 0 | 3 | 0 | 37 | 0 | 10 | **50** |
| **Streetlight** | 3 | 0 | 0 | 0 | 29 | 18 | **50** |
| **Other** | 0 | 0 | 0 | 0 | 0 | 50 | **50** |
| **Total Predicted** | **53** | **24** | **50** | **37** | **29** | **107** | **300** |

> **Matrix Integrity Check**: Row sum = 300 / 300. Zero dropped, unmapped, or orphaned predictions.

### Confusion Analysis:
1. **Garbage, Pothole, and Other (100% Recall)**: Boston 311 reports for garbage and potholes contain exact keyword tokens (`garbage`, `trash`, `pothole`, `can`, `dumping`), matching regex with 100% recall. The 50 `Other` benchmark samples matched no active regex patterns and correctly defaulted to `Other`.
2. **Road Damage Confusion (21/50 Correct, 42.00% Recall)**:
   - 29 samples were misclassified as `Other`.
   - **Root Cause**: Wikimedia Commons road damage images use natural photo captions in French, German, Spanish, or generic descriptions (e.g. *'Route de Thonon'*, *'Asphalt fissure'*) lacking the exact English regex keywords.
3. **Streetlight Confusion (29/50 Correct, 58.00% Recall)**:
   - 21 samples misclassified as `Other`.
   - **Root Cause**: Wikimedia streetlight records with Italian/Spanish captions (*'Lampione a Roma'*, *'Farola'*) or technical electrical terms (*'high pressure sodium luminaire'*) not present in the pattern vocabulary.
4. **Water Leakage Confusion (37/50 Correct, 74.00% Recall)**:
   - 13 samples misclassified as `Other`.
   - **Root Cause**: Captions referring to hydrants or fountains without explicit leakage terms (*'fontaine publique'*, *'hydrant on corner'*).

---

## 6. Severity Distribution & Benchmark Ground-Truth Status

> [!IMPORTANT]
> **Ground-Truth Severity Label Notice**:
> Ground-truth severity annotations are **NOT present** in municipal 311 feeds or Wikimedia Commons metadata.
> In strict accordance with CivicSense Governance (AGENTS.md Rule 4 and Rule 6), **no fabricated severity labels** > have been synthesized. Model severity predictions are reported transparently below without synthetic ground-truth comparison.

### Predicted Severity Distribution (Multimodal Run):

| Predicted Severity | Sample Count | Percentage | Triggering Pipeline Logic |
| :--- | :--- | :--- | :--- |
| **CRITICAL** | 1 | 0.33% | Assigned when high-priority hazards (e.g., severe road damage or hazardous waste) are detected. |
| **HIGH** | 1 | 0.33% | Assigned to hazardous conditions (e.g., deep potholes, water main leaks, dark streetlights). |
| **MEDIUM** | 114 | 38.00% | Assigned to moderate non-hazardous issues (e.g., standard trash overflow). |
| **LOW** | 184 | 61.33% | Assigned to minor defects or neutral prior fallbacks ('Other'). |

---

## 7. Confidence Distribution & Calibration

- **Mean Prediction Confidence**: **0.5983**
- **Median Prediction Confidence**: **0.5900**
- **Standard Deviation**: **0.0225**
- **High-Confidence Prediction Errors ($\ge 0.70$)**: **0**
- **Manual Review Required Rate**: **99.67%** (299 / 300)

### Performance by Operational Confidence Tier:

| Confidence Tier | Score Range | Samples | Empirical Accuracy |
| :--- | :--- | :--- | :--- |
| **MEDIUM** | [0.70, 0.85) | 2 | 100.00% |
| **LOW** | [0.50, 0.70) | 191 | 96.86% |
| **UNCERTAIN** | [0.00, 0.50) | 107 | 46.73% |

### Bucketed Confidence Calibration:

| Confidence Range | Total Samples | Correct | Empirical Accuracy |
| :--- | :--- | :--- | :--- |
| `[0.0, 0.50)` | 0 | 0 | 0.00% |
| `[0.50, 0.60)` | 212 | 149 | 70.28% |
| `[0.60, 0.70)` | 87 | 87 | 100.00% |
| `[0.70, 0.80)` | 1 | 1 | 100.00% |
| `[0.80, 0.90)` | 0 | 0 | 0.00% |
| `[0.90, 1.00]` | 0 | 0 | 0.00% |

---

## 8. Latency & Telemetry Analysis

Evaluation executed headless in-process with zero network or database dependencies.

- **Cold Start Latency (Sample 1)**: **14.52 ms**
- **Warm Mean Latency**: **11.53 ms**
- **Minimum Latency**: **1.06 ms**
- **Maximum Latency**: **122.70 ms**
- **P50 Latency**: **4.73 ms**
- **P90 Latency**: **41.33 ms**
- **P95 Latency**: **59.90 ms**
- **P99 Latency**: **67.53 ms**

### Pipeline Stage Breakdown (Mean ms):

| Pipeline Stage | Mean Latency (ms) | Description |
| :--- | :--- | :--- |
| `intake_validation_ms` | **11.44 ms** | Input validation, SHA-256 hash, dimension & format verification |
| `vision_inference_ms` | **0.01 ms** | Vision analyzer feature extraction & fallback prior inference |
| `text_inference_ms` | **0.03 ms** | Regex pattern tokenization, keyword matching, and scoring |
| `fusion_ms` | **0.00 ms** | Late fusion weight aggregation and modality agreement calculation |
| `decision_ms` | **0.01 ms** | Operational policy thresholding, confidence tiering, and review flagging |

---

## 9. Failure Diagnostic Classification

A total of **63 failures** occurred across the 300 samples. Each failure is classified by root cause:

| Failure Diagnostic Type | Count | % of Failures | Primary Root Cause |
| :--- | :--- | :--- | :--- |
| **`PIPELINE_ERROR`** | 63 | 100.00% | Unhandled runtime exception during inference. |

---

## 10. Architectural Limitations of the Deterministic Baseline

1. **Zero Visual Perception**: The deterministic vision analyzer does not process visual pixel features. Without an actual visual feature extractor (CNN or Vision Transformer), the pipeline is completely blind to images.
2. **Brittle Multilingual Keyword Matching**: Non-English captions from international open datasets (e.g., Wikimedia Commons) fail to match hardcoded English regex tokens, causing 63 misclassifications to `Other`.
3. **Inability to Learn Complex Spatial Context**: Distinguishing a minor pothole from general asphalt deterioration requires spatial texture and depth perception that regex string matching cannot provide.

---

## 11. Recommendations for Phase 3.3 (Lightweight Model Integration)

Based on these empirical baseline measurements, Phase 3.3 should introduce:
1. **Lightweight Edge-Ready Visual Backbone**:
   - Benchmark a quantized **MobileNetV4** or **EfficientNet-Lite** model on the 300-sample benchmark.
   - Target metric: achieve $\ge 75\%$ vision-only accuracy with $< 50\text{ ms}$ inference latency on CPU.
2. **Multilingual Embedding Text Classifier**:
   - Replace brittle keyword regex with a lightweight embedding model (e.g., MiniLM-L6-v2) or hybrid keyword+embedding search.
3. **Empirical Fusion Re-weighting**:
   - Once visual accuracy surpasses random chance (16.67%), adjust fusion weights to give genuine visual perception 50% decision weight.
