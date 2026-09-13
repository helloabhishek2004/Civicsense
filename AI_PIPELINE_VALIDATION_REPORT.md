# CivicSense AI Pipeline, Data Quality & Decision-Support Validation Report

## 1. Executive Summary

- **Total Synthetic Reports**: 24
- **Total Evaluation Pairs**: 20
- **Duplicate Precision**: 100.0%
- **Duplicate Recall**: 100.0%
- **Duplicate F1 Score**: 1.0000
- **False Positive Merges**: 0
- **False Negative Duplicates**: 0
- **Candidate / Uncertain Review Rate**: 35.0%
- **Category Smoke-Test Accuracy**: 70.8%
- **Severity Consistency**: 37.5%
- **Priority Score Bounded & Finite**: True

## 2. Duplicate Matching Results Table

| Pair ID | Scenario | Expected | Predicted Action | Weighted Score | Result Class | Notes |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| `PAIR-TD-01` | TRUE_DUPLICATE | `SAME_ISSUE` | `CANDIDATE` | 0.6790 | **CANDIDATE_REVIEW** | MG Road school pothole: identical category, ~14m distance, s... |
| `PAIR-TD-02` | TRUE_DUPLICATE | `SAME_ISSUE` | `AUTO_LINK` | 0.8091 | **TRUE_POSITIVE** | MG Road school pothole: identical category, ~8m distance, co... |
| `PAIR-TD-03` | TRUE_DUPLICATE | `SAME_ISSUE` | `CANDIDATE` | 0.6376 | **CANDIDATE_REVIEW** | City Market garbage: identical category, ~14m distance, over... |
| `PAIR-TD-04` | TRUE_DUPLICATE | `SAME_ISSUE` | `CANDIDATE` | 0.6181 | **CANDIDATE_REVIEW** | 4th Main water pipe burst: identical category, ~21m distance... |
| `PAIR-GS-01` | GEOGRAPHIC_SEPARATION | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.4591 | **TRUE_NEGATIVE** | MG Road Pothole vs Indiranagar Pothole: ~5 km apart. Must no... |
| `PAIR-GS-02` | GEOGRAPHIC_SEPARATION | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.5523 | **TRUE_NEGATIVE** | Indiranagar 10th Cross vs 14th Cross: ~1.1 km apart. Must no... |
| `PAIR-GS-03` | GEOGRAPHIC_SEPARATION | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.4990 | **TRUE_NEGATIVE** | City Market Garbage vs Residency Road Garbage: ~2.8 km apart... |
| `PAIR-GS-04` | GEOGRAPHIC_SEPARATION | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.4814 | **TRUE_NEGATIVE** | Residency Road Garbage vs Brigade Road Garbage: ~900m apart.... |
| `PAIR-CI-01` | CATEGORY_MISMATCH | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.5105 | **TRUE_NEGATIVE** | Streetlight vs Pothole at Central Park Gate (0m distance). I... |
| `PAIR-CI-02` | CATEGORY_MISMATCH | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.3701 | **TRUE_NEGATIVE** | Streetlight pole vs Water leak at Central Park Gate (~7m). I... |
| `PAIR-CI-03` | CATEGORY_MISMATCH | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.4703 | **TRUE_NEGATIVE** | Pothole vs Water leak at Central Park Gate (~7m). Incompatib... |
| `PAIR-CD-01` | CATEGORY_MISMATCH | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.0840 | **TRUE_NEGATIVE** | Pothole on MG Road vs Garbage at City Market (~2.3 km).... |
| `PAIR-CD-02` | CATEGORY_MISMATCH | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.0892 | **TRUE_NEGATIVE** | Water leakage on 4th Main vs Sidewalk damage on Church St (~... |
| `PAIR-CD-03` | CATEGORY_MISMATCH | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.3301 | **TRUE_NEGATIVE** | Fallen tree vs Open manhole: distinct defect types and ~800m... |
| `PAIR-AM-01` | AMBIGUOUS | `UNCERTAIN` | `CANDIDATE` | 0.4753 | **CORRECT_UNCERTAIN_ROUTING** | MG Road Pothole vs 'This is dangerous' (~3m). Vague text; de... |
| `PAIR-AM-02` | AMBIGUOUS | `UNCERTAIN` | `NEW_ISSUE` | 0.3789 | **DEFERRED_NEW_ISSUE** | MG Road Pothole vs 'Bad road condition' (Road Damage, ~8m). ... |
| `PAIR-AM-03` | AMBIGUOUS | `UNCERTAIN` | `NEW_ISSUE` | 0.6500 | **DEFERRED_NEW_ISSUE** | Identical text but REP-021 has (0, 0) Null Island coords. Mi... |
| `PAIR-AM-04` | AMBIGUOUS | `UNCERTAIN` | `CANDIDATE` | 0.4562 | **CORRECT_UNCERTAIN_ROUTING** | Two vague reports near each other without concrete defect de... |
| `PAIR-SV-01` | GEOGRAPHIC_SEPARATION | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.3506 | **TRUE_NEGATIVE** | Minor shallow cul-de-sac pothole vs arterial road crater (~6... |
| `PAIR-SV-02` | GEOGRAPHIC_SEPARATION | `DIFFERENT_ISSUE` | `NEW_ISSUE` | 0.3879 | **TRUE_NEGATIVE** | Minor leaf litter vs commercial market dump (~5 km apart).... |


## 3. Category & Severity Classification Smoke Test

| Report ID | Expected Cat | Pred Cat | Cat Match | Expected Sev | Pred Sev | Sev Match |
| :--- | :--- | :--- | :---: | :--- | :--- | :---: |
| `SYN-REP-001` | Pothole | Pothole | PASS | HIGH | HIGH | PASS |
| `SYN-REP-002` | Pothole | Road Damage | FAIL | HIGH | CRITICAL | DIFF |
| `SYN-REP-003` | Pothole | Pothole | PASS | MEDIUM | HIGH | DIFF |
| `SYN-REP-004` | Garbage | Garbage | PASS | HIGH | LOW | DIFF |
| `SYN-REP-005` | Garbage | Garbage | PASS | HIGH | LOW | DIFF |
| `SYN-REP-006` | Water Leakage | Road Damage | FAIL | CRITICAL | MEDIUM | DIFF |
| `SYN-REP-007` | Water Leakage | Water Leakage | PASS | CRITICAL | MEDIUM | DIFF |
| `SYN-REP-008` | Pothole | Pothole | PASS | HIGH | HIGH | PASS |
| `SYN-REP-009` | Pothole | Pothole | PASS | MEDIUM | MEDIUM | PASS |
| `SYN-REP-010` | Garbage | Garbage | PASS | MEDIUM | LOW | DIFF |
| `SYN-REP-011` | Garbage | Garbage | PASS | MEDIUM | LOW | DIFF |
| `SYN-REP-012` | Streetlight | Streetlight | PASS | CRITICAL | LOW | DIFF |
| `SYN-REP-013` | Pothole | Pothole | PASS | HIGH | CRITICAL | DIFF |
| `SYN-REP-014` | Water Leakage | Water Leakage | PASS | MEDIUM | MEDIUM | PASS |
| `SYN-REP-015` | Road Damage | Other | FAIL | MEDIUM | LOW | DIFF |
| `SYN-REP-016` | Other | Other | PASS | HIGH | HIGH | PASS |
| `SYN-REP-017` | Other | Other | PASS | CRITICAL | CRITICAL | PASS |
| `SYN-REP-018` | Streetlight | Other | FAIL | HIGH | LOW | DIFF |
| `SYN-REP-019` | Other | Other | PASS | LOW | CRITICAL | DIFF |
| `SYN-REP-020` | Road Damage | Road Damage | PASS | LOW | MEDIUM | DIFF |
| `SYN-REP-021` | Pothole | Pothole | PASS | HIGH | HIGH | PASS |
| `SYN-REP-022` | Pothole | Road Damage | FAIL | LOW | MEDIUM | DIFF |
| `SYN-REP-023` | Garbage | Other | FAIL | LOW | LOW | PASS |
| `SYN-REP-024` | Water Leakage | Other | FAIL | LOW | LOW | PASS |


## 4. Priority Score Boundary Validation

| Scenario ID | Description | Sev | Vol | Rep | Rec | Pers | Final Score | Priority Level |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `SCEN-01-ONE-SEVERE` | One severe report (CRITICAL severity, count=1... | 1.00 | 0.06 | 0.28 | 1.00 | 0.30 | **55.1** | `PriorityLevel.HIGH` |
| `SCEN-02-MANY-LOW` | Many low-severity reports (LOW severity, coun... | 0.25 | 0.95 | 1.00 | 0.91 | 0.55 | **70.4** | `PriorityLevel.CRITICAL` |
| `SCEN-03-MULTI-CRITICAL` | Multiple reports for same severe issue (CRITI... | 1.00 | 0.45 | 0.93 | 0.98 | 0.34 | **78.0** | `PriorityLevel.CRITICAL` |
| `SCEN-04-MISSING-SEVERITY` | Missing AI severity analysis (default fallbac... | 0.25 | 0.11 | 0.49 | 0.74 | 0.39 | **35.1** | `PriorityLevel.MEDIUM` |
| `SCEN-05-MISSING-COORDS` | Missing coordinates (priority does not depend... | 0.75 | 0.16 | 0.63 | 0.91 | 0.36 | **56.5** | `PriorityLevel.HIGH` |
| `SCEN-06-ZERO-REPORTS` | Zero linked reports (empty/closed issue, coun... | 0.25 | 0.00 | 0.00 | 0.00 | 0.00 | **7.5** | `PriorityLevel.LOW` |
| `SCEN-07-CLOSED-ISSUE` | Closed issue (persistence frozen, no recency ... | 0.75 | 0.26 | 0.74 | 0.05 | 0.78 | **52.2** | `PriorityLevel.HIGH` |
| `SCEN-08-CONFLICTING-SEVERITIES` | Conflicting severities (1 LOW, 1 CRITICAL: ma... | 1.00 | 0.11 | 0.49 | 0.95 | 0.32 | **60.0** | `PriorityLevel.HIGH` |

