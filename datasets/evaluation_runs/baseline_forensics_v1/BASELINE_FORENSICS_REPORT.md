# CivicSense — Phase 3.2 Step 6.5: Baseline Forensics, Text-Leakage Audit, and Vision Diagnosis Report

## 1. Executive Summary

This forensic investigation audits the empirical baseline results of the deterministic CivicSense pipeline evaluated in Phase 3.2 Step 6 against the frozen 300-sample balanced benchmark (`datasets/benchmark_v1/`).

- **Benchmark Manifest Hash**: `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b` (Frozen & Verified).
- **Official Baseline Preserved**: `datasets/evaluation_runs/baseline_v1/` remains untouched.
- **Primary Diagnostic Findings**:
  1. **Extreme Text Dependency**: The 79.00% baseline accuracy is driven entirely by explicit lexical keywords. When keywords are masked ([MASKED]), accuracy collapses by **-52.67%** (to 26.33%). When text is empty or neutral, accuracy collapses to **16.67%** (1/6 chance).
  2. **Complete Vision Blindness**: The `PrototypeVisionAnalyzer` is confirmed to possess **zero neural weights, CNN, or ViT backbones**. In production mode, it unconditionally returns `'Other'` with `0.50` confidence. Its 16.67% accuracy is purely random chance against the 50 'Other' samples.
  3. **Confidence Degradation & Review Explosion**: The multimodal fusion formula mathematically depresses confidence by averaging high text confidence (0.85) with the blind vision prior (0.50), resulting in ~0.69 confidence (< 0.70 threshold). This triggers `LOW_CONFIDENCE` human review on **99.67%** (299/300) of reports.
  4. **Source & Caption Bias**: Boston 311 samples achieved **100.00% accuracy** (157/157) due to explicit municipal service request phrases. All 63 failures occurred on Wikimedia Commons records due to natural, descriptive, or multilingual photo captions.

---

## 2. Official Baseline Reference (Preserved)

The official baseline artifacts in `datasets/evaluation_runs/baseline_v1/`, `baseline_vision_only/`, and `baseline_text_only/` have been preserved without modification:

| Evaluation Mode | Accuracy | Macro F1 | Review Required Rate | Mean Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Multimodal (Official)** | 79.00% (237/300) | 0.7934 | 99.67% (299/300) | 11.62 ms |
| **Vision-Only (Official)** | 16.67% (50/300) | 0.0476 | 100.00% (300/300) | 11.47 ms |
| **Text-Only (Official)** | 79.00% (237/300) | 0.7934 | 100.00% (300/300) | 0.08 ms |

---

## 3. Text-Dependency and Text-Leakage Audit

The deterministic text pipeline was evaluated under seven distinct conditions across the identical 300 samples:

| Ablation Condition | Accuracy | Macro F1 | Macro Prec | Macro Rec | Diff from Official | Review Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Original Text** | 79.00% | 0.7934 | 0.8810 | 0.7900 | +0.00% | 100.00% |
| **Lowercased Text** | 79.00% | 0.7934 | 0.8810 | 0.7900 | +0.00% | 100.00% |
| **Whitespace-Normalized Text** | 79.00% | 0.7934 | 0.8810 | 0.7900 | +0.00% | 100.00% |
| **Empty Text (Text-Absent)** | 16.67% | 0.0476 | 0.0278 | 0.1667 | -62.33% | 100.00% |
| **Generic Neutral Text ('Civic issue reported at a public location.')** | 16.67% | 0.0476 | 0.0278 | 0.1667 | -62.33% | 100.00% |
| **Keyword-Masked Text ([MASKED])** | 26.33% | 0.2056 | 0.5128 | 0.2633 | -52.67% | 100.00% |
| **Truncated Text (First 30 characters)** | 71.33% | 0.7100 | 0.8547 | 0.7133 | -7.67% | 100.00% |

### Per-Class Recall by Text Ablation:

| Ablation Condition | Pothole | Road Damage | Garbage | Water Leakage | Streetlight | Other |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `A_original` | 100.0% | 42.0% | 100.0% | 74.0% | 58.0% | 100.0% |
| `B_lowercased` | 100.0% | 42.0% | 100.0% | 74.0% | 58.0% | 100.0% |
| `C_whitespace_normalized` | 100.0% | 42.0% | 100.0% | 74.0% | 58.0% | 100.0% |
| `D_empty` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| `E_generic_neutral` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| `F_keyword_masked` | 0.0% | 32.0% | 0.0% | 20.0% | 6.0% | 100.0% |
| `G_truncated_30` | 100.0% | 24.0% | 100.0% | 58.0% | 46.0% | 100.0% |

### Text Ablation Observations:
- **Case & Whitespace Invariance**: Lowercasing and whitespace normalization produce identical results (79.00%), confirming that standard formatting variations do not perturb the regex engine.
- **Complete Collapse Without Text**: Empty text and Generic neutral text collapse to exactly 16.67% (50/300), predicting `Other` for all 300 samples. This proves that zero visual signal is utilized.
- **Keyword Masking Sensitivity**: When explicit terms (`pothole`, `garbage`, `water`, `light`, `road`, etc.) are masked, accuracy drops from 79.00% to **26.33%**. Pothole and Garbage recall plunge from 100% to **0.00%**.
- **Truncation Robustness on 311 vs Fragility on Wikimedia**: Truncating descriptions to 30 characters retains 71.33% accuracy because Boston 311 prefixes start immediately with canonical terms, whereas descriptive Wikimedia sentences lose keywords.

---

## 4. Vision Pipeline Diagnosis

| Diagnostic Check | Measured Status | Detail |
| :--- | :---: | :--- |
| **Image Load Success** | **100.0%** | 300/300 images exist and read cleanly |
| **Image Preprocessing** | **100.0%** | 300/300 passed magic bytes, dimension, and bomb checks |
| **Neural Network Loaded** | **FALSE** | `PrototypeVisionAnalyzer` has zero CNN/ViT weights |
| **Unique Classes Predicted** | **1** | Only `'Other'` is ever predicted |
| **Neutral Baseline Rate** | **100.0%** | All 300 images assigned `confidence = 0.50, category = Other` |
| **Exceptions Swallowed** | **0** | No crashes or hidden runtime exceptions |
| **Vision-Only Accuracy** | **16.67%** | Exactly 50/300 (1/6 chance matching the 50 'Other' ground-truth samples) |

### Vision Confusion Matrix:
All 300 samples fall into column `Other`:
- Pothole (50): 0 correct, 50 $	o$ Other
- Road Damage (50): 0 correct, 50 $	o$ Other
- Garbage (50): 0 correct, 50 $	o$ Other
- Water Leakage (50): 0 correct, 50 $	o$ Other
- Streetlight (50): 0 correct, 50 $	o$ Other
- Other (50): 50 correct, 50 $	o$ Other (100% recall purely by default prior)

---

## 5. Fusion and Confidence Forensics

| Metric | Count | % of Benchmark | Analysis |
| :--- | :---: | :---: | :--- |
| **Text & Vision Disagreement** | 193 | 64.33% | Text predicts defect category; vision predicts 'Other' |
| **Text & Vision Agreement** | 107 | 35.67% | Only occurs when text also predicts 'Other' |
| **Vision Changed Category** | 0 | 0.00% | Vision never overrides text category |
| **Below Review Threshold (< 0.70)** | 299 | 99.67% | Uncorroborated text confidence drops below 0.70 |
| **Auto-Accepted Reports ($\ge 0.70$)** | 1 | 0.33% | Exactly 1 sample (`pilot_wmlight_13644347`) matched 4 keywords |

### Why Does Multimodal Confidence Suppress Automatic Triage?
The confidence formula is:
$$\text{Confidence} = (0.45 \times \text{Text\_Conf}) + (0.35 \times \text{Vision\_Conf}) + (0.20 \times \text{Modality\_Agreement})$$
- When text matches 1–2 keywords, $\text{Text\_Conf} \approx 0.81 - 0.85$.
- Because vision is blind, $\text{Vision\_Conf} = 0.50$.
- Because one modality is `'Other'`, partial agreement credit gives $\text{Modality\_Agreement} \approx 0.65$.
- Fused score: $(0.85 \times 0.45) + (0.50 \times 0.35) + (0.65 \times 0.20) = 0.3825 + 0.175 + 0.13 = 0.6875 \approx 0.69$.
- Since $0.69 < 0.70$ threshold, **the system flags `LOW_CONFIDENCE` on nearly every report**.

---

## 6. Dataset Source and Caption Bias Audit

| Source Dataset | Total Samples | Correct | Accuracy | Mean Caption Length | Primary Characteristics |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`boston311`** | 157 | 157 | **100.00%** | 22.3 chars | Terse, standardized municipal service tags ('Pothole repair', 'Trash', 'Street light') |
| **`wikimedia_road_damage`** | 45 | 16 | **35.56%** | 243.6 chars | Natural descriptive paragraphs, camera metadata, highway route codes |
| **`wikimedia_streetlight`** | 48 | 27 | **56.25%** | 195.0 chars | Multilingual photo titles (Italian 'lampione', Spanish 'farola', French) |
| **`wikimedia_water`** | 50 | 37 | **74.00%** | 174.3 chars | Geographical hydrologic and burst pipe captions |

### Key Caption Bias Takeaways:
1. **Zero Errors on Municipal 311**: Boston 311 was classified with 100.00% accuracy because municipal 311 intake systems use standardized taxonomy tags in description fields.
2. **All 63 Failures from Open-Data Captions**: Wikimedia Commons records describe real physical defects accurately in imagery, but their text descriptions are human photo captions with high linguistic variance.
3. **Heterogeneity of 'Other'**: The 50 'Other' samples (street signs, construction cones, graffiti, benches) contain zero road/water/light keywords, so the regex engine achieves 100% recall simply by defaulting to `Other`.

---

## 7. Recommended Machine Learning Requirements for Phase 3.3

Based on these forensic facts, Phase 3.3 must implement:
1. **Real Visual Feature Extraction (P0)**:
   - Benchmark a quantized lightweight convolutional or vision transformer backbone (e.g., **MobileNetV4-Small**, **EfficientNet-Lite0**) on CPU.
   - Target: break the 16.67% random baseline and achieve $\ge 70\%$ vision-only accuracy.
2. **Semantic Text Embeddings (P1)**:
   - Replace brittle keyword regex with a multilingual embedding model (e.g., **MiniLM-L6-v2**) or hybrid keyword+embedding scoring.
   - Target: correctly categorize descriptive, natural, and multilingual civic reports.
3. **Adaptive Multimodal Fusion (P1)**:
   - Do not penalize confidence when vision is genuinely uninformative or unavailable.
   - Use calibrated probability outputs rather than rigid heuristic weights.
