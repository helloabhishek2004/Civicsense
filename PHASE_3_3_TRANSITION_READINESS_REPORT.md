# CivicSense — Phase 3.3 End-to-End Transition Readiness Audit Report

**Date**: 2026-09-13  
**Stage**: Phase 3.3 Step 6  
**Document**: Architectural Transition Readiness Audit  
**Author**: Senior ML / MLOps / Systems Architect  

---

## Executive Summary

CivicSense is transitioning from **isolated dataset preparation** to **end-to-end system integration**. 
This report provides a strict, code-backed, evidence-grounded audit of every architectural component in the planned CivicSense reporting pipeline:

$$\text{Mobile Capture} \longrightarrow \text{Edge Preprocessing} \longrightarrow \text{On-Device Vector Gen} \longrightarrow \text{Mobile-to-Server Request} \longrightarrow \text{Server Feature Matching} \longrightarrow \text{Decision Engine} \longrightarrow \text{Storage \& Dashboard}$$

Every component has been verified against running code and configurations in this repository. No component is classified as implemented merely because a placeholder, roadmap, or docstring exists.

---

## 1. Complete Pipeline Status Matrix

| Pipeline Component | Status | Code Evidence | Remaining Work for Production |
| :--- | :---: | :--- | :--- |
| **1. Dataset Foundation** | **VALIDATED** | `datasets/training_v1/manifest.jsonl`, `splits/`, `reports/`, 33 unit tests | Complete Batch 3 curation; reach $\approx 100$/class gate |
| **2. Model Architecture & Interfaces** | **VALIDATED** | `app/services/ai/vision_interface.py`, `datasets/model_research/`, 13 unit tests | Train initial MobileNetV3-Small backbone on server |
| **3. Mobile Image Preprocessing** | **VALIDATED** | `android/.../core/edge/CivicImagePreprocessor.kt`, 76 passing Android unit tests | Bind input dimensions directly to model input resolution ($224 \times 224$) |
| **4. Mobile Text Preprocessing** | **VALIDATED** | `android/.../core/edge/CivicTextPreprocessor.kt`, deterministic token normalization | Calibrate token stopword list against real civic complaints |
| **5. Mobile Vector Generation** | **NOT STARTED** | `EdgeModels.kt` (`embeddingGenerated = false`), `build.gradle.kts` (no ONNX/TFLite runtime) | Integrate LiteRT or ONNX Runtime Mobile; bundle quantized backbone |
| **6. Mobile-to-Server API Contract** | **VALIDATED** | `CivicReportUploadClient.kt`, `backend/app/api/v1/routes/reports.py`, multipart upload | Add optional `vector_embedding` float array field to schema |
| **7. Server Vector Normalization** | **NOT STARTED** | No vector normalization utility in `backend/app/services/` | Implement $L_2$ vector normalization & dimensionality check ($D=1024$ or $576$) |
| **8. Server Feature Matching / Similarity** | **NOT STARTED** | `app/services/similarity/interface.py` (`raise NotImplementedError`) | Implement cosine similarity search & reference prototype vector store |
| **9. Decision Engine & Routing** | **IMPLEMENTED — NOT VALIDATED** | `app/services/ai/decision_engine.py`, `fusion_engine.py` (heuristic thresholds) | Calibrate confidence & agreement thresholds using validation split error analysis |
| **10. Database & Evidence Storage** | **VALIDATED** | Alembic migrations `0001`–`0007`, PostgreSQL 16 models (`Report`, `Evidence`, `AIEvent`) | Add pgvector extension or dedicated embedding table for duplicate search |
| **11. Authority Review Dashboard** | **VALIDATED** | `web-dashboard/`, React 18.3 + TypeScript, 59 passing tests, AI Operations console | Integrate visual similarity candidate review cards |
| **12. Deployment & Observability** | **IMPLEMENTED — NOT VALIDATED** | `docker-compose.yml`, FastAPI health checks, Prometheus middleware | Set up production artifact store for versioned model weights |

---

## 2. Detailed Subsystem Audits

### A. Dataset Foundation
- **Current Size & Balance**: 333 clean samples (50–66 per category across all 6 classes); Batch 3 expanding to $\approx 600$ clean samples.
- **Split Rigor**: Deterministic 80/20 train/validation split with fixed seed `42`; strict incident group disjunction verified ($0$ group overlap).
- **Leakage Prevention**: Zero benchmark collisions or perceptual near-duplicates ($d \le 6$) in clean pool; verified against frozen benchmark (`e988474dd...`).
- **Limitation**: Dataset represents open municipal and web collections; real on-device citizen submission photos will have varying compression artifacts and angles.

### B. Neural Model Pipeline
- **Selected Architecture**: Primary: **MobileNetV3-Small** ($2.5\text{M}$ parameters, $2.5\text{MB}$ INT8, $576$-d embedding, $\approx 12\text{ms}$ mobile latency); Backup: **EfficientNet-Lite0** ($4.7\text{M}$ parameters, $4.7\text{MB}$ INT8, $1280$-d embedding).
- **Current Training Status**: **Zero models trained**. No weights downloaded. Model training is strictly quarantined until dataset curation completes.
- **Dual Representation Strategy**:
  1. *Classification Head*: 6-class softmax output ($P(\text{category} \mid \text{image})$).
  2. *Feature Embedding*: Pre-classification global average pooling vector for similarity search and duplicate clustering.
- **Quantization & Export**: Target format: ONNX (for server & web) and TFLite / LiteRT (INT8 post-training quantization for Android).

### C. Mobile Client (`android/`)
- **Current Implementation**:
  - Jetpack Compose + Material 3 wizard UI with real camera, location, DataStore preferences, and lifecycle-aware polling.
  - Image Preprocessor: EXIF stripping, preview generation, SHA-256 computation, brightness and blur estimation.
  - Text Preprocessor: Character/word counts, keyword hint extraction.
- **Vector Generation Gap**:
  - `ClientProcessingInfo.embeddingGenerated` defaults to `false`.
  - No ML runtime (`tflite` or `onnxruntime-android`) is declared in `build.gradle.kts`.
  - Android client currently transmits raw image + metadata to `/api/v1/reports`.
- **Target Runtime**: Google LiteRT (Play Services runtime to avoid bundling 15MB binary into APK) or standalone ONNX Runtime Mobile ($2.8\text{MB}$ binary).

### D. Server & API Architecture
- **Inbound Endpoint**: `POST /api/v1/reports` accepts multipart form with image file, edge metadata, and citizen info.
- **Current AI Pipeline**: `DemoAIProcessor` / `PrototypeDecisionEngine` orchestrates rule-based text classification, fallback vision analyzer, and heuristic decision fusion.
- **Similarity & Search Gap**:
  - `ISimilarityService` in `backend/app/services/similarity/interface.py` raises `NotImplementedError`.
  - Database schema lacks a vector column or spatial-vector index.

### E. Decision Engine Architecture
- **Current Implementation**:
  - Three-tier decision framework: High Confidence (automatic triage), Medium Confidence (provisional with review flag), Low Confidence (mandatory review).
  - Multi-modal confidence formula: $\text{Conf} = 0.45 \cdot C_{\text{text}} + 0.35 \cdot C_{\text{vis}} + 0.20 \cdot \text{Agreement}$.
- **Severity Handling**:
  - Phase 1 recommendation: **Rule-assisted & Metadata-guided severity** (e.g. depth of pothole, road classification, citizen urgency) with human review fallback. Model-predicted severity should only be enabled after supervised severity labels exist.

### F. Deployment & Infrastructure
- **Containerization**: Backend and PostgreSQL run under Docker Compose.
- **Model Storage**: Model checkpoints should be stored under `backend/app/models/checkpoints/` (gitignored, tracked via SHA-256 metadata).
- **Inference Runtime on Server**: ONNX Runtime Python (`onnxruntime`) or PyTorch CPU (`torch`).

---

## 3. Recommended 5-Stage Integration Roadmap

To avoid fragile big-bang integrations, CivicSense must follow a disciplined, progressive staging plan:

```
[Stage 1: Server Model Inference] ──► [Stage 2: Server Feature Matching] ──► [Stage 3: Mobile Vector Generation]
                                                                                       │
[Stage 5: Staging Deployment] ◄────── [Stage 4: End-to-End Decision Loop] ◄────────────┘
```

### Stage 1: Controlled Server Inference (Immediate Priority)
- Train MobileNetV3-Small backbone on curated training dataset (`datasets/training_v1/`).
- Evaluate on validation split and frozen benchmark (`datasets/benchmark_v1/`).
- Export trained model to ONNX format.
- Replace `MockVisionModel` in `app/services/ai/vision_analyzer.py` with real `ONNXServerVisionModel` implementing `VisionModel` interface.
- *Deliverable*: Server can classify uploaded report images with real CNN probabilities.

### Stage 2: Server-Side Prototype Feature Matching
- Extract 576-d feature embeddings for all verified training samples.
- Store reference prototype embeddings in memory or SQLite / PostgreSQL.
- Implement `ISimilarityService` using normalized cosine similarity ($L_2$ dot product).
- Return top-$k$ nearest neighbors and similarity distance score.
- *Deliverable*: Server can identify duplicate submissions and near-identical defects across town.

### Stage 3: Mobile On-Device Vector Generation
- Quantize MobileNetV3-Small to INT8 TFLite format ($< 3\text{MB}$).
- Add LiteRT dependency to `android/app/build.gradle.kts`.
- Implement `CivicVectorGenerator.kt` in `android/.../core/edge/`.
- Verify embedding parity between mobile-generated vectors and server-generated vectors ($r > 0.98$).
- *Deliverable*: Mobile phone computes 576-d vector locally in $< 35\text{ms}$.

### Stage 4: Closed-Loop Decision Engine
- Calibrate confidence thresholds using validation split Receiver Operating Characteristic (ROC) analysis.
- Connect server feature matching + visual prediction + text NLP into `decision_engine.py`.
- Route reports below threshold ($C < 0.75$) to municipal human review queue.
- *Deliverable*: Fully explainable, automated decision routing with audited human review fail-safes.

### Stage 5: End-to-End Integration & Staging Deployment
- Integrate Mobile $\to$ Server vector transmission (optional client vector speeds up matching).
- Validate full pipeline on Android emulator against local FastAPI backend.
- Verify Authority Dashboard updates in real time via polling.
- *Deliverable*: Working civic intelligence platform ready for staged municipal trial.
