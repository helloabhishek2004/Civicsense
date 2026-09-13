# CivicSense — Results and Limitations

## Automated Test Results

| Suite | Tests | Status |
|---|---|---|
| Backend (pytest) | 470 | PASS |
| Frontend (Vitest) | 85 | PASS |
| Total | 555 | PASS |

Additional quality checks:
- Ruff linting: PASS (E, W, F, I rules clean)
- TypeScript compilation: PASS (0 errors)
- Frontend production build: PASS

## Synthetic Evaluation Results

### Duplicate Detection (Synthetic Benchmark, n=300)

| Metric | Value | Notes |
|---|---|---|
| Precision | 100.0% | Zero false merges |
| Recall | 100.0% | Zero missed duplicates |
| F1 Score | 1.0000 | Perfect on synthetic pairs |
| Candidate review rate | 35.0% | Safely deferred to human review |

> **Important:** The 100% precision, recall, and F1 results apply only to the current synthetic benchmark and must not be interpreted as real-world model accuracy.

### Text Model Comparison (Validation Set, n=119)

| Model | Accuracy | Macro F1 |
|---|---|---|
| Deterministic baseline | 70.59% | 0.6974 |
| TF-IDF + LogReg | 88.24% | 0.8807 |
| MiniLM Trained Head | 89.08% | 0.8858 |
| Ensemble (α=0.1) | 89.08% | 0.8858 |

### Multimodal Fusion (Benchmark, n=300)

| Configuration | Accuracy | Macro F1 |
|---|---|---|
| Text-only baseline | 79.00% | 0.7934 |
| Vision-only (MobileNetV3) | 43.33% | 0.3938 |
| Multimodal fused | 79.67% | 0.7910 |

### Statistical Significance

- McNemar's paired test (MiniLM vs deterministic): p = 0.0001 (statistically significant)
- Bootstrap 95% CI for accuracy difference: [+4.33pp, +12.33pp]

## Operational Workflow Coverage

| Workflow | Status |
|---|---|
| Report submission | IMPLEMENTED |
| Report retrieval and filtering | IMPLEMENTED |
| Issue listing and detail | IMPLEMENTED |
| Match review (approve/reject) | IMPLEMENTED |
| Alternate issue relinking | IMPLEMENTED |
| Repeat review protection (409) | IMPLEMENTED |
| Priority recomputation | IMPLEMENTED |
| Department assignment | IMPLEMENTED |
| Assignment acknowledgment | IMPLEMENTED |
| Job completion | IMPLEMENTED |
| Department rejection with reassignment | IMPLEMENTED |
| Audit trail | IMPLEMENTED |
| Health monitoring | IMPLEMENTED |
| Pilot dataset seeding | IMPLEMENTED |

## Known Limitations

### Prototype Authentication
- The `X-Reviewer-ID` header accepts any non-empty string
- No JWT, session management, or role-based access control
- Suitable only for controlled demonstrations
- Production requires authenticated identity and authorization

### PostgreSQL Validation Status
- Smoke test script created (`scripts/smoke_test_postgres.py`)
- Not executed against a live PostgreSQL instance
- Test suite runs on SQLite in-memory

### Browser E2E Status
- No Playwright or Selenium configured in the project
- Frontend tests run via Vitest (unit/integration only)
- No automated browser-level validation

### Synthetic Data Limitation
- All evaluation metrics are on manufactured data
- Real-world civic reports have more noise, ambiguity, and variation
- Text embeddings are trained on general web text, not civic domain text
- Performance on real municipal data is unknown

### GPS Cutoff Limitation
- Reports within 50 meters are considered spatially co-located
- Real GPS accuracy varies from 3 meters (good conditions) to 50+ meters (urban canyons)
- No temporal clustering or trajectory analysis

### Severity Heuristic Limitation
- Severity is determined by keyword matching ("danger", "emergency", "school")
- Not ML-classified or contextually aware
- May misclassify severity for novel or ambiguous descriptions

### No Image Classification
- The current similarity pipeline uses text embeddings only
- Image classification (MobileNetV3) was piloted but not integrated into production
- No visual duplicate detection or defect surface analysis

### Limited Category Taxonomy
- Six canonical categories: Pothole, Road Damage, Garbage, Water Leakage, Broken Streetlight, Other
- Bridge category mapping is manually configured
- No automatic category discovery or expansion

### No Real-Time Notifications
- No WebSocket or Server-Sent Events for live updates
- Dashboard relies on polling (5–10 second intervals)
- No citizen-facing status push notifications

### No Multilingual Support
- Text analysis is English-only
- No translation or cross-language similarity
