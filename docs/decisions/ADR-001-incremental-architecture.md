# ADR-001: Incremental Architecture and Foundational Domain Principles

## Status
Accepted

## Context
CivicSense is a multimodal AI-assisted civic intelligence system combining machine vision, natural language processing, spatial clustering, data mining, and human-in-the-loop verification.

Attempting to build the entire system simultaneously introduces significant risk of architectural sprawl, untestable abstractions, synthetic mock logic, and heavy dependency bloat (e.g. installing PyTorch, OpenCV, DINOv2, vector databases, and message brokers before the core data model and API contracts are proven).

Furthermore, traditional civic complaint systems often suffer from architectural flaws such as collapsing submissions into single mutable complaint rows, losing raw evidence when generating embeddings, conflating model confidence with physical severity, and assuming AI predictions represent final authority.

## Decisions

### 1. Incremental Phasing
We develop CivicSense incrementally across disciplined phases:
- **Phase 0 (Foundation)**: Core repository, database models, lifecycle state machine, typed API contracts, mobile scaffolding, testing, and developer tooling. No heavy ML dependencies or synthetic AI logic.
- **Subsequent Phases**: Vision baseline, text baseline, multimodal fusion, decision engine, duplicate detection, and data mining.

### 2. Edge / Cloud Separation
Mobile devices handle privacy-preserving preprocessing, image quality assessment, and lightweight local inference. Heavy multimodal fusion, similarity search, geospatial clustering, and data mining reside strictly on the server. The edge output is treated as preliminary evidence, not authoritative ground truth.

### 3. Report vs. Issue Distinction
- `Report`: An individual submission from a citizen (containing specific description, timestamp, device metadata, and attached evidence).
- `Issue`: An underlying civic condition on the ground (e.g., a specific pothole at Elm & 5th).
Multiple distinct reports can map to a single real-world issue, creating a priority signal without duplicating civic work orders.

### 4. Separate Confidence, Severity, and Priority
We explicitly decouple:
- `Confidence`: Model certainty in classification ($0.0 \dots 1.0$).
- `Severity`: Physical magnitude or risk of the defect (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- `Priority`: Urgency of administrative response, derived from severity, recurrence, location sensitivity, and report volume.
These are stored in separate, explicit fields.

### 5. Prediction vs. Decision Separation
AI models output predictions and feature representations. The `Decision Engine` interprets these outputs against business rules and confidence bounds to decide whether a report can proceed automatically or requires human review.

### 6. Evidence Preservation
Original images and raw text descriptions are never discarded in favor of embeddings. Embeddings are lossy representations tied to specific model versions; original evidence must remain retrievable for human verification, legal audits, and future model retraining.

### 7. Model Provenance Tracking
All AI outputs record their full provenance: `model_name`, `model_version`, `preprocessing_version`, and `embedding_model`.

## Consequences
- **Positive**: Clean interfaces, zero premature dependency bloat, high testability, transparent auditability, and protection against model incompatibility.
- **Negative**: Requires explicit foreign keys and join tables (`Report`, `Issue`, `Evidence`, `AIAnalysis`, `ModelVersion`) rather than a single flat complaint table.
