# CivicSense — Phase 4A Statistical Validation Report
**Date**: 2026-09-13  
**Auditor**: Senior Statistical Evaluation Specialist  
**Evaluation Target**: Paired Significance, Discordance Forensics & 10,000-Iteration Bootstrap Intervals  
**Benchmark Artifact**: `datasets/benchmark_v1/benchmark_dataset.jsonl` (SHA-256: `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b`)  
**Sample Size**: $n=300$  
**Evaluation Seed**: 42

---

## 1. Methodology & Formal Hypotheses

To establish whether semantic text modeling introduces measurable, generalizable value over the frozen deterministic baseline, we conduct paired hypothesis tests on identical benchmark samples ($n=300$):

- **Null Hypothesis ($H_0$)**: The marginal probability of a correct prediction is identical between the deterministic baseline and the semantic text model ($P(\text{Det Correct}) = P(\text{MiniLM Correct})$), i.e., $b = c$ in discordant pairs.
- **Alternative Hypothesis ($H_1$)**: The semantic text model significantly alters classification correctness ($P(\text{Det Correct}) \ne P(\text{MiniLM Correct})$).
- **Decision Criterion**: Reject $H_0$ if two-sided $p < 0.05$ AND the 95% bootstrap confidence interval for accuracy difference excludes zero.

---

## 2. Primary Contrast: MiniLM (Trained Head) vs Deterministic Text Baseline

### 2.1 Paired 2x2 Contingency Table
```
                               MiniLM Correct (y2=1)   MiniLM Wrong (y2=0)     Row Total
Deterministic Correct (y1=1)        n11 = 230               n10 = 7 (b)       237 (79.00%)
Deterministic Wrong (y1=0)          n01 = 32 (c)            n00 = 31           63 (21.00%)
Column Total                        262 (87.33%)             38               300
```

### 2.2 Discordant Analysis & Cell Definitions
- **$n_{11}$ (Consensus Correct)**: 230 samples (76.67%) where both classifiers succeed.
- **$b = n_{10}$ (MiniLM Regressions)**: 7 samples (2.33%) where the deterministic baseline is correct but MiniLM is incorrect.
- **$c = n_{01}$ (MiniLM Improvements)**: 32 samples (10.67%) where the deterministic baseline is incorrect (defaulting to `Other`) but MiniLM predicts the true category.
- **$n_{00}$ (Shared Failures)**: 31 samples (10.33%) where both classifiers fail.
- **Total Discordant Pairs ($b + c$)**: $7 + 32 = 39$ ($> 25$, satisfying the asymptotic sample size criterion for continuity-corrected $\chi^2$).
- **Net Sample Differential ($c - b$)**: $+25$ samples (+8.33 percentage points).

### 2.3 McNemar Test Statistic & Exact p-value
Using Edwards' continuity-corrected McNemar test:
$$\chi^2 = \frac{(|b - c| - 1)^2}{b + c} = \frac{(|7 - 32| - 1)^2}{39} = \frac{24^2}{39} = \frac{576}{39} = 14.7692$$

- **Test Statistic**: $\chi^2 = 14.7692$ ($df = 1$)
- **Two-Sided p-value**: **$p = 0.000122$** ($p < 0.001$)
- **Decision**: **REJECT $H_0$** at $\alpha = 0.05$ (and at $\alpha = 0.001$).
- **Conclusion**: The performance lift of MiniLM over the deterministic baseline is statistically significant on this benchmark distribution.

---

## 3. Paired Bootstrap Resampling (10,000 Iterations)

To evaluate sampling variability without normality assumptions, 10,000 paired bootstrap resamples ($n=300$ with replacement) were executed on identical random index vectors across all models (seed 42).

| Metric | Point Estimate | Bootstrap Mean | Bootstrap Median | Bootstrap Std | 95% Percentile CI |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Deterministic Baseline Accuracy** | 79.00% | 79.00% | 79.00% | 0.0233 | **[74.33%, 83.67%]** |
| **MiniLM Accuracy** | 87.33% | 87.30% | 87.33% | 0.0189 | **[83.33%, 90.67%]** |
| **Accuracy Difference ($\Delta$)** | **+8.33 pp** | **+8.29 pp** | **+8.33 pp** | **1.9982 pp** | **[+4.33 pp, +12.33 pp]** |
| **Deterministic Macro F1** | 0.7934 | 0.7920 | 0.7924 | 0.0217 | [0.7490, 0.8341] |
| **MiniLM Macro F1** | 0.8703 | 0.8690 | 0.8692 | 0.0178 | [0.8332, 0.9023] |
| **Macro F1 Difference ($\Delta$)** | **+0.0769** | **+0.0770** | **+0.0771** | **0.0220** | **[+0.0338, +0.1204]** |

### Statistical Rigor Assessment
- The entire 95% bootstrap confidence interval for accuracy difference is strictly positive: **$[+4.33\text{ pp}, +12.33\text{ pp}]$**.
- Zero is excluded by more than 2 full standard errors.
- The Macro F1 difference CI similarly confirms sustained non-zero lift: **$[+0.0338, +0.1204]$**.

---

## 4. Secondary Contrasts

### 4.1 TF-IDF Control Baseline vs Deterministic Baseline
- **Contingency Matrix**: $n_{11} = 230$, $n_{10} = 7$, $n_{01} = 30$, $n_{00} = 33$
- **Total Discordant**: $37$ ($b=7$, $c=30$)
- **McNemar Statistic**: $\chi^2 = 12.9730$, **$p = 0.000316$** (statistically significant)
- **Bootstrap 95% CI Difference**: **$[+3.67\text{ pp}, +11.67\text{ pp}]$**
- **Finding**: Conventional n-gram TF-IDF also significantly outperforms deterministic rules on this benchmark.

### 4.2 MiniLM vs TF-IDF Control Baseline
- **Contingency Matrix**:
  - Both correct ($n_{11}$): 249
  - TF-IDF correct, MiniLM wrong ($b$): 11
  - TF-IDF wrong, MiniLM correct ($c$): 13
  - Both wrong ($n_{00}$): 27
- **Total Discordant**: 24 ($\le 25 \implies$ Exact Binomial Test)
- **Exact Binomial p-value**: **$p = 0.8388$**
- **Accuracy Lift**: +0.67 pp (+2 net correct predictions)
- **Finding**: MiniLM slightly outperforms TF-IDF (+2 samples, +0.60 pp F1), but the difference between MiniLM and TF-IDF is **not statistically significant** ($p = 0.8388$). MiniLM and TF-IDF have comparable raw accuracy on this $n=300$ benchmark, though MiniLM offers far superior calibration (ECE 0.0578 vs 0.1744) and natural language generalization.

### 4.3 Conservative Ensemble ($\alpha=0.1$) vs Deterministic Baseline
- **Contingency Matrix**: $n_{11} = 233$, $n_{10} = 4$, $n_{01} = 31$, $n_{00} = 32$
- **Total Discordant**: 35 ($b=4$, $c=31$, Net $+27$ samples)
- **McNemar Statistic**: $\chi^2 = 19.3143$, **$p = 0.000011$** ($p < 10^{-4}$)
- **Bootstrap 95% CI Difference**: **$[+5.33\text{ pp}, +12.67\text{ pp}]$**
- **Finding**: Blending 10% keyword certainty with 90% MiniLM probability produces the strongest statistical significance of any system evaluated.

---

## 5. Statistical Scope, Generalization Boundaries & Duplicate Sensitivity

> [!IMPORTANT]
> **Boundary of Proven Generalization**: The statistical claims in this report apply strictly to the population distribution represented by the frozen benchmark (`benchmark_dataset.jsonl`, $n=300$). While the accuracy difference ($+8.33\text{ pp}$, 95% CI $[+4.33, +12.33]\text{ pp}$, $p = 0.000122$) is statistically unequivocal, broader real-world generalization across diverse external municipal jurisdictions, multilingual citizen inputs, and complex composite defects remains a hypothesis to be monitored and evaluated in Phase 4B and production staging.

### 5.1 Duplicate Sensitivity Cross-Check
As detailed in `duplicate_sensitivity_report.json`:
- **Caption Deduplication ($n=293$)**: Excluding the 7 web caption collisions maintains MiniLM's statistical lift (+8.53 pp over deterministic baseline, 87.03% vs 78.50%).
- **Strict Deduplication ($n=145$)**: Excluding all 155 overlapping records (including generic 311 titles like `"Request for Pothole Repair"`) widens MiniLM's lift over the deterministic baseline to **+17.24 pp** (73.79% vs 56.55%), and the official ensemble achieves a **+18.62 pp** lift (75.17% vs 56.55%).
- **Conclusion**: The statistical lift of MiniLM does not depend on memorized repeated titles across train/test splits. Rather, removing repeated titles degrades the keyword-dependent rule engine far more severely than the semantic model.
