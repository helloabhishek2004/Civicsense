# CivicSense Pilot Artifact Bundle (v0.3.5)
**Freeze Date**: 2026-09-13  
**Status**: Frozen and Statistically Validated  
**Benchmark SHA-256**: `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b`

## Contents
1. `evaluation_manifest.json`: System provenance, environment, git commit, and hyperparameters.
2. `benchmark_results.json`: Canonical reproduced accuracy, macro F1, and selective triage metrics.
3. `statistical_tests.json`: McNemar paired significance test results and contingency table.
4. `bootstrap_confidence_intervals.json`: 10,000-iteration paired bootstrap intervals and exact selective bounds.
5. `coverage_risk_curve.csv`: Multi-threshold sweep evaluating coverage, selective accuracy, and errors.
6. `coverage_risk_report.json`: Operating points analysis (Conservative, Balanced, High-Coverage) and policy ablations.
7. `calibration_report.json`: Mathematical calibration audit, Brier scores, ECE, NLL, and reliability diagrams.
8. `latency_report.json`: 8-stage micro-benchmarking breakdown across 200 measured iterations.
9. `classwise_analysis.json`: Per-class metrics, confusion matrices, overturned cases, and trade-off analysis.

## Key Conclusions
- **Accuracy Lift**: Fused accuracy is **79.67%** (239/300) vs **79.00%** (237/300) text baseline (+0.67 pp, +2 samples).
- **Statistical Significance**: McNemar p-value is **p = 0.8145** (not statistically significant on n=300).
- **Selective Auto-Triage**: 81 / 300 reports accepted with 100% observed accuracy (81/81 correct, 95% CI: [96.37%, 100.00%]).
- **Deployment Recommendation**: Balanced operating point (tau=0.60, agreement required, Other excluded, 73% review rate). Autonomous dispatch without officer review is NOT approved.
