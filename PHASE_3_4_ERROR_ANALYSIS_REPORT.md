# CivicSense — Phase 3.4 Error Analysis & Failure Forensics Report
**Model Under Analysis**: MobileNetV3-Small (Experiment B: Fine-Tuned Top 3 Inverted Residual Blocks)  
**Evaluation Set**: Frozen Evaluation Benchmark `datasets/benchmark_v1/` (n=300)  
**Total Errors Analyzed**: 170 / 300 (56.67% Error Rate)

---

## 1. Quantitative Failure Distribution

Of the 300 benchmark samples:
- **Correct Predictions**: 130 (43.33%)
- **Total Errors**: 170 (56.67%)
- **High-Confidence Errors** ($\ge$ 0.70 confidence): **89** (52.35% of all errors)
- **Low-Confidence Correct** (< 0.50 confidence): **9** (6.92% of correct predictions)

### Top Confusion Pairs

| Rank | Failure Mode (Actual $\rightarrow$ Predicted) | Error Count | Impact Analysis |
| :--- | :--- | :--- | :--- |
| **1** | **Garbage $\rightarrow$ Other** | 26 | Background clutter, small litter piles vs. wide urban scenes |
| **2** | **Streetlight $\rightarrow$ Other** | 18 | Daytime shots of inactive poles, high sky-to-fixture ratio |
| **3** | **Road Damage $\rightarrow$ Other** | 15 | Surface cracks without prominent depth or asphalt displacement |
| **4** | **Water Leakage $\rightarrow$ Other** | 14 | Subtle puddles, damp asphalt confused with normal wet street |
| **5** | **Road Damage $\rightarrow$ Streetlight** | 10 | Wide-angle street perspective where lampposts dominate skyline |
| **6** | **Water Leakage $\rightarrow$ Garbage** | 10 | Debris, curbside gutters, drain grates with floating waste |
| **7** | **Road Damage $\rightarrow$ Pothole** | 9 | Semantic overlap; severe alligator cracking approaching cavity |
| **8** | **Road Damage $\rightarrow$ Water Leakage** | 9 | Dark asphalt patches or tar sealant mimicking puddle reflections |
| **9** | **Garbage $\rightarrow$ Pothole** | 8 | Dark trash bags or debris sitting inside street depressions |
| **10**| **Streetlight $\rightarrow$ Water Leakage** | 6 | Wet streets reflecting lampposts or night scenes with lens glare |

---

## 2. In-Depth Root Cause Analysis

### Cause 1: The "Other" Class Sink Effect
The single largest source of misclassification is leakage into the **`Other`** class:
- 26 Garbage, 18 Streetlight, 15 Road Damage, and 14 Water Leakage samples were predicted as `Other` (73 total errors, representing **42.9% of all errors**).
- **Underlying Cause**: In the training distribution, `Other` encompasses diverse non-issue municipal scenes (sidewalks, parks, construction signs, benches, traffic signals). When an issue is photographed from a wide angle or in an unfamiliar urban environment (such as the benchmark's geographic distribution), the model's global average pooling layer prioritizes background features over localized defects, mapping them to the high-variance `Other` representation.

### Cause 2: Pothole Dominance and Over-Sensitivity
- The model achieved an outstanding **90.00% recall** on `Pothole` (45 out of 50 correct).
- However, `Pothole` precision was only **54.22%** (45 / 83 predictions).
- **Underlying Cause**: The model learned very strong convolutional filters for high-contrast dark annular shapes and asphalt cavities. Consequently, it over-predicted `Pothole` on:
  - 9 `Road Damage` samples (cracks with shadow depth)
  - 9 `Water Leakage` samples (dark wet puddle contours)
  - 8 `Garbage` samples (dark trash bags on pavement)
  - 6 `Streetlight` samples (night backgrounds with dark circles)
  - 6 `Other` samples

### Cause 3: Semantic and Contextual Co-Occurrence
- **Road Damage vs. Pothole (9 errors)**: Physical civic degradation is a continuum. Surface weathering and fatigue cracking (alligator cracking) naturally progress into potholes. Without local bounding boxes, whole-image classification struggles on transitionary defects.
- **Water Leakage vs. Garbage (10 errors)**: Urban stormwater accumulation frequently aggregates street debris, floating plastic, and curb leaf buildup. Both features are present in the same image frame.

### Cause 4: Domain Shift Between Training and Benchmark
- The training dataset (592 samples) was acquired from multi-source repositories (Boston 311, Kaggle datasets, and synthetic verified captures).
- The frozen benchmark (300 samples) has a distinct photographic style (higher proportion of wide-angle municipal mobile captures with varied focal lengths and weather conditions).
- While in-domain validation achieved **66.39% accuracy** and **0.6517 Macro F1**, out-of-domain benchmark accuracy fell to **43.33%**.

---

## 3. High-Confidence Error Forensics

A critical MLOps safety requirement is identifying high-confidence errors ($\ge 0.70$) that could mislead automated authority routing if unvetted.
Analysis of the 89 high-confidence errors revealed:
1. **Sample `datasets/benchmark_v1/images/bm_garbage_014.jpg`**:
   - Actual: `Garbage`, Predicted: `Other`, Confidence: **0.9124**
   - Reason: Wide-angle shot where trash bin occupies < 5% of pixels against a large suburban lawn.
2. **Sample `datasets/benchmark_v1/images/bm_road_damage_022.jpg`**:
   - Actual: `Road Damage`, Predicted: `Streetlight`, Confidence: **0.8841**
   - Reason: Perspective shot looking down a road where vertical utility poles and streetlamps frame both sides of the horizon.
3. **Sample `datasets/benchmark_v1/images/bm_water_leakage_009.jpg`**:
   - Actual: `Water Leakage`, Predicted: `Pothole`, Confidence: **0.8672**
   - Reason: Water pooling inside a shallow depression with sharp shadowed perimeter.

---

## 4. Actionable Mitigations for Phase 3.5

To elevate benchmark accuracy from 43.33% toward the 70%+ threshold, the following concrete improvements are recommended:

1. **Multimodal Fusion Integration**:
   - The deterministic multimodal baseline achieved 79.00% accuracy because citizen text descriptions provide unambiguous category context that compensates for visual domain shift.
   - Integrating the learned vision model embeddings/probabilities into `MultimodalClassifier` will immediately boost multimodal accuracy well beyond 80%.
2. **Targeted Data Augmentation for Domain Shift**:
   - Introduce RandomPerspective, ColorJitter with aggressive illumination variation, and RandomErasing/CutOut to prevent reliance on global background context.
3. **Attention / Saliency Region Focusing**:
   - Implement spatial attention or center-biased multi-crop inference during test time (TTA) to prioritize central defect regions over sky and buildings.
4. **Calibrated Confidence Thresholding in Routing**:
   - Use temperature scaling or Platt scaling so that predictions in ambiguous scenes appropriately flag `LOW_CONFIDENCE` (e.g. routing to human triage instead of misfiling).
