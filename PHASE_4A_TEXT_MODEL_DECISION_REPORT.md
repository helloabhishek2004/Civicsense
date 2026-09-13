# CivicSense — Phase 4A Text Model Decision & Architecture Report
**Date**: 2026-09-13  
**Authors**: Senior ML Engineer, NLP Architect & Production AI Systems Reviewer  
**Phase Target**: Phase 4A Standalone Text Intelligence Decision Gate  
**Current System State**: Phase 3.5.1 Multimodal Baseline Frozen (79.67% Fusion, 79.00% Deterministic Text, 43.33% Vision)  
**Frozen Benchmark**: `datasets/benchmark_v1/benchmark_dataset.jsonl` (SHA-256: `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b`)

---

## 1. Decision Gate Synthesis

| Evaluation Criteria | Requirement / Threshold | Observed Result | Status |
| :--- | :--- | :--- | :--- |
| **Statistical Superiority over Rule Baseline** | $p < 0.05$ & 95% CI excludes 0 | **$p = 0.000122$**, CI: **[+4.33 pp, +12.33 pp]** | **PASSED** |
| **Accuracy Lift on Frozen Benchmark** | Measurable positive net samples | **+8.33 pp** (+25 net correct samples, 262 vs 237) | **PASSED** |
| **Calibration Quality (ECE)** | $\le 0.15$ for probability fusion | **ECE = 0.0578** (Brier: 0.1925, NLL: 0.4372) | **PASSED** |
| **CPU Inference Latency** | Mean $\le 50\text{ ms}$, p95 $\le 100\text{ ms}$ | **Mean = 9.69 ms**, p50 = 7.99 ms, **p95 = 19.37 ms** | **PASSED** |
| **Cold-Start Startup Time** | $\le 500\text{ ms}$ | **90.17 ms** | **PASSED** |
| **Host Process Memory (OS RSS)** | Operational on desktop/server backend | **Post-load: 521.14 MB** (load $\Delta$: **+66.20 MB**, peak: 541.36 MB) | **PASSED** |
| **In-Flight Transient Memory** | Minimal per-request allocations | **0.07 MB** (`tracemalloc` peak during forward pass) | **PASSED** |
| **Licensing & Offline Integrity** | Permissive OSS, strictly offline | **Apache 2.0**, local safetensors, no network | **PASSED** |
| **Benchmark Non-Modification** | SHA-256 unchanged | Verified byte-identical before & after | **PASSED** |

---

## 2. In-Depth Comparative Evaluation

### 2.1 MiniLM vs Deterministic Rule Engine
- **The Core Trade-off**:
  - The deterministic rule engine is unbeatable when explicit category keywords are present (**100.0% accuracy on $n=151$ keyword-containing samples**).
  - However, the rule engine is brittle on natural language descriptions where citizens describe problems without canonical keywords (collapsing to **57.7% on $n=149$ keyword-free samples**).
  - MiniLM-L6-v2 closes this gap dramatically, scoring **77.8% on keyword-free samples (+20.13 pp lift)**.
- **Statistical Verdict**: The lift (+8.33 pp, $p = 0.000122$) is genuine, robust across 10,000 bootstrap iterations, and not an artifact of random sampling.

### 2.2 MiniLM vs TF-IDF + Logistic Regression
- **The Empirical Reality**:
  - Conventional n-gram TF-IDF proved to be a formidable control baseline, scoring **86.67% (260/300)** on the frozen benchmark.
  - MiniLM scored **87.33% (262/300)**, an advantage of +2 samples.
  - The paired McNemar test between MiniLM and TF-IDF yielded **$p = 0.8388$**, confirming that raw accuracy on this $n=300$ benchmark is not statistically distinguishable between the two.
- **Why MiniLM Is the Superior Architecture for CivicSense**:
  1. **Calibration Quality**: MiniLM's ECE is **0.0578**, compared to TF-IDF's **0.1744**. MiniLM outputs smooth, well-calibrated posterior probabilities that reflect true uncertainty—a critical requirement for downstream Bayesian multimodal fusion.
  2. **Subword & Semantic Generalization**: TF-IDF requires exact token or n-gram overlap. In citizen reporting, typos ("pot hole", "drainge", "streat light"), synonyms, and descriptive circumlocutions ("huge crater that almost flipped my scooter") cause out-of-vocabulary degradation in TF-IDF, whereas MiniLM maps them to the correct embedding neighborhood.
  3. **Multimodal Embeddings**: The dense 384-dimensional vector space produced by MiniLM can be projected into shared multimodal embedding spaces (e.g. CLIP / image-text alignment), which sparse TF-IDF vectors cannot support.

### 2.3 Standalone vs Ensemble Configuration & Selection Provenance
- Combining the deterministic rule engine with MiniLM in a linear probability ensemble:
  $$P_{\text{ensemble}} = \alpha P_{\text{det}} + (1 - \alpha) P_{\text{minilm}}$$
- **Validation Tuning ($n=119$)**:
  - $\alpha = 0.00$ (Pure MiniLM): 89.08% Acc, 0.8858 Macro F1
  - $\alpha = 0.10$ (Conservative Ensemble): **89.08% Acc**, **0.8858 Macro F1** (0 regressions on exact keyword queries)
  - Based on validation results, $\alpha = 0.10$ was frozen as the **official preselected ensemble configuration** prior to benchmark evaluation to safeguard keyword reliability.
- **Benchmark Evaluation ($n=300$)**:
  - **Official Preselected Ensemble ($\alpha = 0.10$)**: **88.00% Acc**, **0.8777 Macro F1** (cuts regressions vs deterministic baseline to 4)
  - **Exploratory Post-Hoc Probe ($\alpha = 0.50$)**: *88.33% Acc*, *0.8824 Macro F1* (+1 additional correct prediction)
- **Governance Decision**: In accordance with Rule 0 and strict scientific integrity, $\alpha = 0.50$ is documented as an exploratory observation but **is not promoted** to official status, preserving true out-of-sample validation provenance.

---

## 3. Formal Architectural Decision

### Decision 1: Designate MiniLM as the Leading Candidate for Phase 4B Multimodal Fusion
**Decision**: **APPROVED AS CANDIDATE**.
The `all-MiniLM-L6-v2` transformer with trained logistic regression head is designated as CivicSense's primary semantic text candidate for multimodal vision fusion integration in Phase 4B.
- **Status**: Staged, audited, trained, calibrated, and frozen under `models/all_minilm_l6_v2/`.
- **Scope**: Evaluated as a standalone text intelligence module. Not an unconditional replacement of all text subsystems until multimodal fusion is validated in Phase 4B.

### Decision 2: Maintain Calibrated Lexical-Semantic Ensemble
**Decision**: **APPROVED**.
To avoid regressing on high-certainty municipal service request keywords, the production text classification interface exposes `EnsembleTextModel` parameterized with $\alpha = 0.10$ (official champion selection manifest) and fallback to pure MiniLM ($\alpha = 0.0$) when rules produce zero keyword signal.

### Decision 3: Preserve Deterministic Text Analyzer as Invariant Control
**Decision**: **MANDATED**.
The original `PrototypeTextPatternAnalyzer` remains 100% untouched and functional as a baseline control and fallback engine (`PrototypeTextModel`).

### Decision 4: Phasing Boundary for Multimodal Fusion Integration
**Decision**: **HELD FOR PHASE 4B**.
Per project governance and Rule 0 / Step boundaries:
- Phase 4A is strictly isolated to standalone text intelligence research and evaluation.
- No changes to `MultimodalFusionEngine` or vision models were made in Phase 4A.
- Integration of MiniLM probabilities into the multimodal fusion pipeline and end-to-end selective auto-triage will take place in **Phase 4B**.

---

## 4. Operational & Deployment Architecture

```
[Citizen Issue Description (Text)]
               │
               ├──► [PrototypeTextModel] (Deterministic Keywords) ──► P_det (6-class)
               │                                                          │
               └──► [MiniLMTextEncoder] ──► 384-d Embedding               │
                            │                                             │
                            ▼                                             │
                    [Trained LR Head] ───────────────► P_sem (6-class)    │
                            │                                             │
                            ▼                                             │
                    [EnsembleTextModel] ◄─────────────────────────────────┘
                 (P_ens = 0.10 * P_det + 0.90 * P_sem)
                            │
                            ▼
              [TextPrediction Output Schema]
              - Top Category (e.g., 'Pothole')
              - Calibrated Confidence (e.g., 0.89)
              - 6-Class Probability Distribution
              - Outcome Status (SUCCESS, LOW_CONFIDENCE, etc.)
```

### Mobile / Android Edge Path
- Current desktop/server inference runs unquantized PyTorch FP32 on CPU in **9.69 ms**.
- Model weights: 90.87 MB FP32 safetensors.
- Mobile roadmap:
  - **Theoretical INT8 Weight-Only Estimate**: **~22.7 MB** ($90.87\text{ MB} \times 0.25$).
  - **Packaged Mobile Runtime Consideration**: Packaging for edge deployment (ONNX Runtime / LiteRT) involves the inference engine binary (`libonnxruntime.so` ~10-15 MB), tokenizer vocabularies, and runtime activation memory, which will be empirically measured during mobile edge build integration.
