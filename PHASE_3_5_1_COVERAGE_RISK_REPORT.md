# CivicSense — Phase 3.5.1 Coverage-Risk Analysis Report
**Date**: 2026-09-13  
**Auditor**: Production Safety Reviewer & MLOps Architect  
**Subject**: Selective Auto-Triage Threshold Sweep, Operating Profiles & Policy Ablations  
**Evaluation Benchmark**: Frozen Benchmark (n=300)

---

## 1. Operating Point Taxonomy & Pilot Recommendation

The CivicSense selective triage system balances **Coverage** (percentage of reports dispatched autonomously without officer burden) against **Risk** (frequency of erroneous automated dispatches).

### Defined Operating Profiles

| Operating Profile | Conf Threshold ($	au$) | Modality Agreement | Exclude `Other` | Concordance Thresh | Auto-Accepted | Coverage | Selective Accuracy | False Dispatches | Human Review |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Conservative** | 0.70 | Required | Yes | 0.50 | 81 / 300 | 27.00% | 100.00% (81/81) | 0 | 219 (73.0%) |
| **Balanced (Recommended)**| **0.60** | **Required** | **Yes** | **0.50** | **81 / 300** | **27.00%** | **100.00% (81/81)** | **0** | **219 (73.0%)** |
| **High-Coverage** | 0.50 | Required | Yes | 0.40 | 81 / 300 | 27.00% | 100.00% (81/81) | 0 | 219 (73.0%) |

### Recommendation Rationale
We recommend **Balanced Profile ($	au = 0.60$, Agreement Required, Other Excluded, Concordance $\ge 0.50$)** for the pilot deployment. 
- It achieves **27.00% automated coverage** on the benchmark with **zero observed false dispatches**.
- It maintains high assurance by routing 73.00% of complex, ambiguous, or discordant reports to human officers.
- Autonomous municipal dispatch without human-in-the-loop triage is **NOT approved**.

---

## 2. Multi-Threshold Sweep Table (Standard Safety Policy)

```
Conf Thresh  Auto-Accepted  Human Review  Coverage  Selective Acc  Selective Error  False Auto-Accepts  High-Conf Errors
0.50         81             219           27.00%    100.00%        0.00%            0                   22
0.55         81             219           27.00%    100.00%        0.00%            0                   15
0.60         81             219           27.00%    100.00%        0.00%            0                   15
0.65         81             219           27.00%    100.00%        0.00%            0                   15
0.70         81             219           27.00%    100.00%        0.00%            0                   15
0.75         81             219           27.00%    100.00%        0.00%            0                   10
0.80         81             219           27.00%    100.00%        0.00%            0                   9
0.85         81             219           27.00%    100.00%        0.00%            0                   7
0.90         77             223           25.67%    100.00%        0.00%            0                   3
```

Notice that between $	au = 0.50$ and $	au = 0.85$, the auto-accepted cohort is identical ($81$ samples) because the category agreement and `Other` exclusion filters act as the binding constraints. At $	au = 0.90$, coverage drops slightly from $81$ to $77$ ($25.67\%$).

---

## 3. Safety Policy Ablation Forensics (Analytical Study)

*Warning: These ablations were executed strictly for analytical risk quantification and must NEVER be deployed to live production.*

| Ablation Setting | Conf Thresh ($	au$) | Auto-Accepted | Coverage | Selective Accuracy | False Auto-Accepts | Intercepted by Policy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard Policy (Baseline)** | 0.60 | 81 | 27.00% | **100.00%** | **0** | 247 |
| **Agreement Optional** | 0.60 | 88 | 29.33% | **100.00%** | **0** | 223 |
| **`Other` Included** | 0.60 | 133 | 44.33% | **88.72%** | **15** | 167 |
| **Safety Policy Completely Disabled** | 0.60 | 151 | 50.33% | **90.07%** | **15** | 0 |
| **Safety Policy Completely Disabled** | 0.50 | 191 | 63.67% | **88.48%** | **22** | 0 |

### Critical Safety Findings:
1. **The `Other` Exclusion is Essential**: When `Other` is permitted into the auto-dispatch stream, coverage rises to 44.33%, but **15 false dispatches** occur, dropping selective accuracy to **88.72%**. This proves that `Other` represents an intrinsically heterogeneous catch-all category that requires mandatory human triage.
2. **The Full Safety Policy Prevents Catastrophic Errors**: Without safety policy interception at $	au = 0.50$, **22 erroneous reports** would be dispatched directly to municipal work crews. The CivicSense policy successfully intercepts all 22.
