# CivicSense — Phase 3.5.1 Statistical Validation Report
**Date**: 2026-09-13  
**Auditor**: Statistical Evaluation Specialist  
**Evaluation Scope**: Paired Significance, Bootstrap Resampling & Selective Uncertainty Bounds  
**Sample Size**: n=300 (Frozen Benchmark)  
**Seed**: 42 (Deterministic)

---

## 1. McNemar Paired Significance Test

Because the deterministic text baseline and the multimodal fusion engine were evaluated on the **exact same 300 benchmark samples**, an independent two-sample test (e.g. two-proportion z-test) is invalid. We employ McNemar's paired test based strictly on discordant classifications.

### 2x2 Correctness Contingency Table
```
                                Fusion Correct    Fusion Wrong      Total
Text Correct                          231               6 (b)        237 (79.00%)
Text Wrong                              8 (c)          55             63 (21.00%)
Total                                 239              61            300
```

### Discordant Cell Definitions
- **$n_{11} = 231$**: Both systems correct (Consensus).
- **$n_{10} (b) = 6$**: Text correct, Fusion wrong (Fusion regressions).
- **$n_{01} (c) = 8$**: Text wrong, Fusion correct (Fusion improvements / overturned cases).
- **$n_{00} = 55$**: Both systems wrong (Shared defect complexity).
- **Total Discordant Pairs**: $b + c = 6 + 8 = 14$.

### Test Formulation & Execution
Because the total discordant count ($14 \le 25$) is small, the asymptotic chi-square approximation with continuity correction can be imprecise. We execute the **exact two-sided binomial test** under the null hypothesis $H_0: p = 0.5$:
$$p = 2 	imes \sum_{i=0}^{\min(b, c)} inom{b+c}{i} 0.5^{b+c} = 2 	imes \sum_{i=0}^6 inom{14}{i} 0.5^{14} = 0.790527$$

### Statistical Results Summary
- **Text Accuracy**: 79.00% (237 / 300)
- **Fusion Accuracy**: 79.67% (239 / 300)
- **Accuracy Difference**: **+0.67 percentage points** (+2 net correct predictions)
- **McNemar Method**: Exact Binomial Test (two-sided)
- **Test Statistic**: $k = \min(6, 8) = 6.0$
- **Two-Sided p-value**: **$p = 0.7905$**
- **Asymptotic 95% Confidence Interval for Difference**: **$[-1.78, +3.11]	ext{ pp}$**
- **Null Hypothesis Rejection**: **FAILED TO REJECT $H_0$** at $lpha = 0.05$.

### Scientific Interpretation
- **Measurable Improvement**: Yes. Multimodal fusion correctly classified 2 additional real-world incidents out of 300.
- **Statistical Significance**: **No**. With $n=300$ and only 14 discordant pairs, the benchmark lacks statistical power to reject the null hypothesis of equal accuracy. The observed lift could arise by chance under sampling variance.
- **Practical Implication**: Visual intelligence provides undeniable qualitative disambiguation (rescuing 8 samples where text defaulted to `Other`), but claims of broad statistical superiority are scientifically unfounded on this sample size.

---

## 2. Paired Bootstrap Confidence Intervals (10,000 Iterations)

To characterize metric variability without making parametric distribution assumptions, we executed paired bootstrap resampling ($10,000$ iterations, seed $42$).

In each iteration, the identical vector of $300$ resampled indices was evaluated across ground truth, text predictions, and fusion predictions. Macro F1 was recomputed from scratch across all 6 classes on every iteration.

| Metric | Point Estimate | Bootstrap Mean | Bootstrap Median | Standard Error | Percentile 95% CI |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Text Accuracy** | 79.00% | 79.00% | 79.00% | 0.0233 | **[74.33%, 83.67%]** |
| **Fusion Accuracy** | 79.67% | 79.65% | 79.67% | 0.0228 | **[75.00%, 84.00%]** |
| **Accuracy Difference ($\Delta$)** | **+0.67 pp** | +0.65 pp | +0.67 pp | 1.2384 pp | **[-1.67 pp, +3.00 pp]** |
| **Text Macro F1** | 0.7934 | 0.7920 | 0.7924 | 0.0217 | **[0.7490, 0.8341]** |
| **Fusion Macro F1** | 0.7910 | 0.7893 | 0.7894 | 0.0225 | **[0.7456, 0.8326]** |
| **Macro F1 Difference ($\Delta$)** | **-0.0024** | -0.0027 | -0.0028 | 0.0124 | **[-0.0263, +0.0218]** |

Notice that the 95% confidence interval for paired accuracy difference $[-1.67, +3.00]	ext{ pp}$ crosses zero, independently corroborating the McNemar test result.

---

## 3. Selective Evaluation & Uncertainty Bounding on Zero Errors

In the auto-accepted dispatch cohort, the system accepted **81 out of 300 benchmark reports (27.00% coverage)** and achieved **81 correct predictions out of 81 (100.00% observed accuracy, 0 false dispatches)**.

### Mathematical Honesty About Zero Observed Errors
Reporting 81/81 as "proof of zero operational risk" is scientifically invalid. Zero errors on a finite sample size $n=81$ indicates that the true population error rate is small, but strictly positive.

### Binomial Confidence Bounds
Using the exact **Clopper-Pearson method** (based on the beta distribution quantile for $k=n$):
$$	ext{Lower Bound} = lpha^{1/n} = 0.05^{1/81} pprox 0.9637$$

- **Observed Selective Accuracy**: 100.00% (81 / 81)
- **Clopper-Pearson Exact 95% Confidence Interval**: **$[96.37\%, 100.00\%]$**
- **Wilson Score Continuity-Adjusted 95% CI**: **$[95.47\%, 100.00\%]$**
- **Selective Coverage (Wilson 95% CI)**: **$[22.29\%, 32.29\%]$** (Point: 27.00%)
- **False Dispatch Rate on Accepted Cohort**: 0.00% (95% upper bound: **$3.63\%$**)
- **False Dispatch Rate on Full Benchmark**: 0.00% (95% upper bound: **$0.98\%$**)

### Audit Conclusion
At 95% statistical confidence, the true operational accuracy of the auto-accepted dispatch stream is bounded above **96.37%**. While this validates the pilot gate for controlled operational review, the potential $3.63\%$ error margin reinforces why human oversight cannot be fully removed.
