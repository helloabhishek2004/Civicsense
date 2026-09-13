# CivicSense — Phase 3.2 Step 1: Repository Audit Before Dataset Infrastructure

**Document ID:** `PHASE_3_2_STEP_1_REPOSITORY_AUDIT.md`  
**Phase:** 3.2 (Dataset Acquisition, Curation & Baseline Evaluation — Step 1 Audit)  
**Author:** Senior Software Architect, Backend Engineer & ML Systems Engineer  
**Date:** September 2026  
**Status:** Audit Complete — Zero Production Code Modified — Zero Dataset Weights Downloaded

---

## Executive Summary

Phase 3.1 proposed an architectural blueprint for civic dataset discovery, licensing review, and evaluation benchmarking. Before any datasets are downloaded or new modules are created, this forensic audit inspects the actual repository state to verify canonical contracts, identify existing reusable utilities, examine directory layouts, establish offline execution feasibility, and define a minimal, risk-free file plan.

### Key Audit Highlights
1. **Canonical Slugs in Code**: The backend uses discrete string identifiers (`"Pothole"`, `"Road Damage"`, `"Garbage"`, `"Water Leakage"`, `"Streetlight"`, `"Other"`) defined in `PredictionNormalizer.CATEGORY_LABELS` and `PrototypeTextPatternAnalyzer.CATEGORY_KEYWORDS`. There is **no** `Category` enum in `app/models/enums.py`.
2. **Offline Execution Capability**: The underlying deterministic AI sub-services (`PrototypeVisionAnalyzer`, `PrototypeTextPatternAnalyzer`, `PrototypeFusionEngine`, `PrototypeDecisionEngine`, and `PredictionNormalizer`) are **100% pure Python functions/classes** that can be executed directly offline in-memory without a PostgreSQL database, an HTTP server, or network connectivity.
3. **Reusable Production Quality Gates**: `app/services/ai/input_validator.py` (`InputValidator`) already implements magic-byte sniffing (JPEG, PNG, WebP), payload sizing, decompression bomb mitigation, and full pixel buffer decodes, as well as NFKC Unicode text normalization and spam defense. These must be reused rather than reimplemented.
4. **Existing ML Directory Structure**: An `ml/` tree was scaffolded during Phase 0 (`ml/datasets/`, `ml/evaluation/`, `ml/preprocessing/`, `ml/training/`, `ml/experiments/`). The Phase 3.2 file plan will strategically reconcile root-level dataset directories with this existing workspace.
5. **Strict Dependency Invariant**: The backend runs Python 3.14.3 (`requires-python = ">=3.11"`) managed strictly via `backend/pyproject.toml`. PyTorch, TensorFlow, ONNX Runtime, and Transformers are absent and must **NOT** be added in Phase 3.2. Deduplication (pHash/dHash) can be implemented via the existing `pillow>=10.0.0` library with zero new dependencies.

---

## Section A: Repository Findings

### A.1 Relevant File Paths & Responsibilities

| Subsystem / Layer | File Path | Primary Architectural Responsibility | Reusability in Phase 3.2 |
| :--- | :--- | :--- | :--- |
| **Model Enums** | [`backend/app/models/enums.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/models/enums.py) | Defines `SeverityLevel`, `PriorityLevel`, `ReportStatus`, `AIJobStatus`, `AIProcessingStage`, `AssignmentStatus`. | Direct import of `SeverityLevel` and `PriorityLevel`. |
| **Prediction Normalizer** | [`backend/app/services/ai/normalized_prediction.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/services/ai/normalized_prediction.py) | Maps raw engine outputs to canonical schemas; houses authoritative `CATEGORY_LABELS` dictionary; enforces confidence tiers. | **Authoritative reference** for category slugs, display labels, and confidence thresholds. |
| **Prediction Schema** | [`backend/app/schemas/normalized_prediction.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/schemas/normalized_prediction.py) | Pydantic v2 schemas: `NormalizedPrediction`, `CategoryPredictionItem`, `PredictionConfidenceTier`. | Direct benchmark target schema for baseline outputs. |
| **Input Validator** | [`backend/app/services/ai/input_validator.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/services/ai/input_validator.py) | Rigorous two-phase media validation (magic bytes, dimensions, 25M pixel bomb guard) and NFKC text sanitization. | **Primary reusable utility** for dataset image and text integrity validation. |
| **Text Pattern Analyzer** | [`backend/app/services/ai/text_analyzer.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/services/ai/text_analyzer.py) | Lexical keyword pattern matching across categories and urgency vocabularies. | Reusable for multimodal and unimodal text benchmark evaluation. |
| **Vision Analyzer** | [`backend/app/services/ai/vision_analyzer.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/services/ai/vision_analyzer.py) | Deterministic visual heuristic extractor. Disregards filenames (`AI_ENABLE_FILENAME_HEURISTICS=False`). | Evaluated component in offline vision baseline. |
| **Multimodal Fusion** | [`backend/app/services/ai/fusion_engine.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/services/ai/fusion_engine.py) | Cross-evaluates vision and text signals; computes `modality_agreement` ($0.10 - 1.0$). | Evaluated component for cross-modal consistency. |
| **Decision Engine** | [`backend/app/services/ai/decision_engine.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/services/ai/decision_engine.py) | Synthesizes final category, severity, priority, and review gates (`review_required`). | Evaluated component for triage routing and abstention. |
| **Demo Orchestrator** | [`backend/app/services/ai/demo_processor.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/services/ai/demo_processor.py) | Stateful database-backed orchestrator managing `AIJob` and `AIJobEvent` transitions. | Reference flow; offline harness will decouple this from database transactions. |
| **Configuration** | [`backend/app/core/config.py`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/backend/app/core/config.py) | Central `Settings` (thresholds: High 0.80, Med 0.65, Review 0.70, Agreement 0.60). | Source of truth for confidence governance thresholds. |
| **Android Taxonomy** | [`android/app/src/main/java/com/civicsense/data/model/Models.kt`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/android/app/src/main/java/com/civicsense/data/model/Models.kt) | `ReportCategory` enum on citizen mobile client. | Verification of cross-platform category alignment. |
| **Dashboard Taxonomy** | [`dashboard/src/types/models.ts`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/dashboard/src/types/models.ts) | `CivicCategory` TypeScript union type. | Verification of dashboard authority alignment. |

### A.2 Existing Reusable Utilities
1. **`InputValidator.validate_image_bytes(raw_bytes, declared_mime_type)`**:
   - Inspects binary magic bytes (`\xff\xd8\xff` for JPEG, `\x89PNG\r\n\x1a\n` for PNG, `RIFF...WEBP` for WebP).
   - Enforces 10MB payload ceiling.
   - Enforces pixel dimension constraints ($[64, 8192]$ px).
   - Traps decompression bombs ($> 25,000,000$ pixels).
   - Performs full `image.verify()` + `image.load()` to catch truncated or corrupted streams.
   - Calculates deterministic SHA-256 hash.
   - Returns `ValidatedImageResult` containing width, height, pixels, MIME type, and hash.
2. **`InputValidator.validate_and_sanitize_text(text)`**:
   - Rejects empty and whitespace-only text.
   - Trims and normalizes Unicode to NFKC (safeguarding Indic and Arabic characters).
   - Strips non-printable ASCII control characters ($< 32$ except `\n`, `\r`, `\t`).
   - Compresses repeated punctuation runs ($\ge 20$ chars) to 3 characters with warning.
   - Rejects repeated non-punctuation spam runs ($\ge 20$ chars) with `TextValidationError`.
   - Returns `ValidatedTextResult` containing cleaned text, character count, and word count.
3. **`PredictionNormalizer.normalize(...)`**:
   - Accepts raw outputs from analyzers.
   - Enforces confidence bounds $[0.0, 1.0]$ and maps to `PredictionConfidenceTier`.
   - Populates candidate ranking list (`top_predictions`).
   - Produces safe, schema-compliant `NormalizedPrediction`.

### A.3 Existing Project Directory Conventions
- **Monorepo Structure**:
  - `android/`: Native Android citizen application.
  - `dashboard/`: Vite + React authority dashboard.
  - `backend/`: FastAPI application (`app/`), database migrations (`alembic/`), tests (`tests/`), uploaded assets (`uploads/`).
  - `mobile/`: React Native / Expo scaffold.
  - `shared/`: Shared JSON schemas.
  - `scripts/`: Dev runner scripts (`dev.ps1`, `dev.sh`, `verify_api_live.py`).
  - `ml/`: Pre-scaffolded directory tree (`datasets/`, `evaluation/`, `experiments/`, `preprocessing/`, `training/`).
- **Missing Infrastructure for Phase 3.2**:
  - No `datasets/benchmark_v1/` directory exists yet.
  - No dataset downloader scripts exist under `scripts/datasets/`.
  - No headless offline evaluation harness exists under `backend/app/evaluation/`.
  - No dataset-independent `EvaluationSample` schema exists.
  - No perceptual hashing (`pHash`) deduplication module exists.

---

## Section B: Canonical Contract Verification

### B.1 Canonical Category Mapping Matrix

| Canonical Category | Exact Slug in Backend Code | Display Label (`PredictionNormalizer.CATEGORY_LABELS`) | Android Client Enum | Dashboard Union (`CivicCategory`) | Alignment / Mismatch with Phase 3.1 Report |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pothole** | `"Pothole"` | `"Pothole / Road Surface Cavity"` | Mapped under `ROAD_DAMAGE` (`"Road Damage"`) | `'Pothole'` | **Exact Match**: Fully aligned across backend, dashboard, and Phase 3.1. |
| **Road Damage** | `"Road Damage"` | `"Road Surface Crack & Fissure Pattern"` | `ROAD_DAMAGE` (`"Road Damage"`) | `'Road Damage'` | **Exact Match**: Fully aligned across all components. |
| **Garbage** | `"Garbage"` | `"Solid Waste & Debris Accumulation"` | `GARBAGE` (`"Garbage"`) | `'Garbage'` | **Minor Label Clarification**: Report referred to `"Garbage / illegal dumping"`. Code slug is strictly `"Garbage"`. |
| **Water Leakage** | `"Water Leakage"` | `"Water Pipeline Leak & Fluid Pooling"` | `WATER_LEAKAGE` (`"Water Leakage"`) | `'Water Leakage'` | **Exact Match**: Fully aligned across all components. |
| **Streetlight** | `"Streetlight"` | `"Street Lighting & Luminaire Defect"` | *Missing on Android* (reported as `INFRASTRUCTURE` / `NOT_SURE`) | `'Streetlight'` | **Architectural Finding**: Backend and Dashboard define `Streetlight` as canonical, routing to `ELECTRICAL`. Android currently lacks a dedicated `STREETLIGHT` chip. For Phase 3.2 benchmark, `"Streetlight"` is strictly maintained. |
| **Other** | `"Other"` | `"Unclassified Civic Issue"` | `OTHER` / `NOT_SURE` (`"Other"`) | `'Other'` | **Minor Label Clarification**: Report referred to `"Other / unknown"`. Code slug is strictly `"Other"`. |
| **Drainage** *(Auxiliary)* | `"Drainage"` | `"Stormwater Drainage & Clogged Sewer"` | *None* | `'Drainage'` | Auxiliary dictionary label. Maps into `Water Leakage` for initial 6-class benchmark. |
| **Infrastructure** *(Auxiliary)* | `"Infrastructure"` | `"Damaged Public Footpath / Structure"` | `INFRASTRUCTURE` (`"Infrastructure"`) | `'Infrastructure'` | Auxiliary label. Maps into `Road Damage` or `Other` for initial 6-class benchmark. |

### B.2 Production Category Representation Truth
> [!IMPORTANT]
> In `backend/app/models/enums.py`, there is **no Python `Enum` class** for categories.
> Category values are tracked as `str` (bounded by `VARCHAR(64)` in the database).
> The canonical validation authority is `PredictionNormalizer.CATEGORY_LABELS` in `backend/app/services/ai/normalized_prediction.py`.

---

## Section C: Deterministic Processor Execution Path

### C.1 Architectural Execution Flow

```
Raw Inputs: [Image File / Bytes] + [Problem Description String]
                      │
                      ▼
        ┌─────────────────────────────┐
        │       InputValidator        │
        │ - Magic byte check          │
        │ - Dimension / Bomb check    │
        │ - NFKC Unicode text clean   │
        └──────────────┬──────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
┌──────────────────┐       ┌────────────────────────┐
│  Vision Analyzer │       │ Text Pattern Analyzer  │
│  - Heuristics    │       │ - Keyword dictionary   │
│  - Filename stem │       │ - Urgency terms        │
│    ignored       │       │ - Confidence: [0.65-0.92]
└────────┬─────────┘       └───────────┬────────────┘
         │                             │
         └─────────────┬───────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │        Fusion Engine        │
        │ - Cross-modal concordance   │
        │ - Modality agreement score  │
        │   (0.10 - 1.0; None if uni) │
        └──────────────┬──────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │       Decision Engine       │
        │ - Category synthesis        │
        │ - Confidence calculation    │
        │ - Review policy gates       │
        └──────────────┬──────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │    Prediction Normalizer    │
        │ - Schema validation         │
        │ - Candidate ranking list    │
        │ - Confidence tier mapping   │
        └──────────────┬──────────────┘
                       │
                       ▼
      Output: Canonical NormalizedPrediction
```

### C.2 Detailed Path Specifications
1. **Entry Point**:
   - In production API: `DeterministicDemoProcessor.process(db: Session, job: AIJob, report: Report) -> AIJob` (`backend/app/services/ai/demo_processor.py:46`).
   - In offline evaluation: `OfflineDeterministicEvaluator.evaluate(image_bytes: bytes | None, text: str | None) -> NormalizedPrediction`.
2. **Input Format**:
   - Vision: Attached image file or in-memory byte buffer (JPEG, PNG, WebP).
   - Text: Citizen complaint text description string (UTF-8).
3. **Output Format**:
   - Canonical Pydantic schema: `NormalizedPrediction` (`backend/app/schemas/normalized_prediction.py`).
   - Key attributes: `predicted_category: str`, `confidence: float`, `confidence_tier: PredictionConfidenceTier`, `severity: SeverityLevel`, `priority: PriorityLevel`, `evidence_agreement: float | None`, `requires_review: bool`, `review_reasons: list[str]`, `top_predictions: list[CategoryPredictionItem]`, `timing_breakdown: dict[str, Any]`.
4. **How Image and Text Are Processed**:
   - *Vision*: `PrototypeVisionAnalyzer.analyze()` checks image presence. If `AI_ENABLE_FILENAME_HEURISTICS=False` (production default), it produces a neutral baseline (`category = "Other"`, `confidence = 0.50`, `severity = LOW`) unless explicit simulation metadata is passed.
   - *Text*: `PrototypeTextPatternAnalyzer.analyze()` scans normalized text for regex word matches against `CATEGORY_KEYWORDS` and `URGENCY_KEYWORDS`. If matches are found, `confidence = min(0.92, 0.65 + (len(matches) * 0.08))`. If no keywords match, returns `category = "Other"`, `confidence = 0.50`.
5. **How Confidence Is Produced**:
   - When multimodal (both image and text present):
     $$\text{Confidence} = \text{round}(0.45 \cdot \text{conf}_{\text{text}} + 0.35 \cdot \text{conf}_{\text{vision}} + 0.20 \cdot \text{modality\_agreement}, 2)$$
   - When unimodal text-only:
     $$\text{Confidence} = \text{round}(\text{conf}_{\text{text}} \cdot 0.70, 2)$$
     *(0.70 administrative policy penalty applied for missing visual corroboration)*.
6. **How Abstention / Review Is Produced**:
   - Evaluated against centralized thresholds in `app/core/config.py`:
     - If `confidence < AI_REVIEW_CONFIDENCE_THRESHOLD` (0.70) $\to$ `review_required = True`, `review_reason = "LOW_CONFIDENCE"`.
     - If `evidence_agreement < AI_MODALITY_AGREEMENT_THRESHOLD` (0.60) $\to$ `review_required = True`, `review_reason = "MODALITY_DISAGREEMENT"`.
     - If `final_category == "Other"` $\to$ `review_required = True`, `review_reason = "UNCLASSIFIED_ISSUE"`.
     - If unimodal fallback $\to$ `review_required = True`, `review_reason = "UNIMODAL_TEXT_FALLBACK"`.
7. **Offline Feasibility Without HTTP Server**:
   - **Confirmed: 100% Feasible.** The five core sub-services (`InputValidator`, `PrototypeVisionAnalyzer`, `PrototypeTextPatternAnalyzer`, `PrototypeFusionEngine`, `PrototypeDecisionEngine`, and `PredictionNormalizer`) have zero coupling to FastAPI, Uvicorn, or PostgreSQL. They can be invoked directly in Python scripts or unit tests with zero server overhead.

---

## Section D: Proposed Phase 3.2 File Plan

To keep dataset storage and evaluation tools completely isolated from production application code and database migrations, the following minimal, modular file layout is recommended:

```
CivicSense/
├── datasets/                                 # [NEW] Git-ignored dataset repository
│   ├── .gitignore                            # Ignores raw/ and benchmark_v1/images/
│   ├── README.md                             # Legal provenance, source URLs & licenses
│   ├── raw/                                  # Ephemeral source downloads
│   │   ├── rdd2022/
│   │   ├── taco/
│   │   └── boston311/
│   └── benchmark_v1/                         # Mini-benchmark distribution
│       ├── images/                           # Standardized UUID images (sample_000001.jpg)
│       ├── benchmark_dataset.jsonl           # 300 canonical sample records with provenance
│       ├── manifest.json                     # Checksums, category counts, generation time
│       └── splits.json                       # Stratified indices (all 300 in benchmark split)
│
├── backend/
│   └── app/
│       └── evaluation/                       # [NEW] Dedicated evaluation package
│           ├── __init__.py
│           ├── schema.py                     # EvaluationSample & BenchmarkManifest schemas
│           ├── evaluator.py                  # Offline evaluator wrapping deterministic sub-services
│           ├── metrics.py                    # Macro F1, Per-class metrics, 6x6 Confusion Matrix
│           └── runner.py                     # Headless benchmark execution engine
│
└── scripts/
    └── datasets/                             # [NEW] Controlled data curation scripts
        ├── README.md                         # Instructions for running acquisition & curation
        ├── download_sample_data.py           # Selective downloader (50 samples per category)
        ├── deduplicate.py                    # Pure-Python pHash / dHash near-duplicate filter
        ├── build_benchmark.py                # Compiles raw data into benchmark_dataset.jsonl
        └── run_baseline_evaluation.py        # Runs baseline and outputs Markdown report
```

### Purpose of Proposed Modules:
1. `backend/app/evaluation/schema.py`: Defines the `EvaluationSample` Pydantic contract (preserving sample ID, source dataset, source record ID, canonical category, original category, license, attribution, SHA-256, pHash, and review status).
2. `backend/app/evaluation/evaluator.py`: Encapsulates offline execution of the deterministic pipeline on an `EvaluationSample` without spinning up a database.
3. `backend/app/evaluation/metrics.py`: Computes Macro-F1, Micro-F1, Balanced Accuracy, Per-Class Precision/Recall, 6x6 Confusion Matrix, Abstention Rate, Selective Accuracy, and p50/p95 latency.
4. `scripts/datasets/deduplicate.py`: Computes exact SHA-256 and 64-bit difference hashes (`dHash`) using existing `PIL.Image` without external dependencies. Rejects pairs with Hamming distance $\le 4$.
5. `scripts/datasets/run_baseline_evaluation.py`: Executes the 300-sample mini-benchmark through `evaluator.py`, records all predictions, and writes `BASELINE_EVALUATION_REPORT.md`.

---

## Section E: Dependency Policy

### E.1 Current Backend Dependencies (`backend/pyproject.toml`)
- **Runtime**: `fastapi>=0.115.0`, `uvicorn[standard]>=0.30.0`, `pydantic>=2.8.0`, `pydantic-settings>=2.4.0`, `sqlalchemy>=2.0.30`, `alembic>=1.13.0`, `psycopg[binary]>=3.2.0`, `pillow>=10.0.0`.
- **Dev**: `pytest>=8.0.0`, `httpx>=0.27.0`, `ruff>=0.6.0`, `mypy>=1.11.0`.

### E.2 Phase 3.2 Dependency Commitments
- **Zero Heavy ML Libraries**: Phase 3.2 must **NOT** add:
  - `torch` / `torchvision` (PyTorch)
  - `tensorflow`
  - `onnx` / `onnxruntime`
  - `transformers`
  - `ultralytics`
  - `sentence-transformers`
- **Zero Large Weights**: No model checkpoints, pretrained weights, or multi-gigabyte files will be downloaded or committed.
- **Zero New Package Requirements**:
  - Image decoding, resizing, and pixel operations: Handled entirely by `pillow>=10.0.0` (already installed).
  - Schema validation and JSONL serialization: Handled entirely by `pydantic>=2.8.0` (already installed).
  - Mathematical metrics (Macro-F1, confusion matrix, percentiles): Handled using Python standard library (`math`, `statistics`, `collections.Counter`). No need even for `scikit-learn` or `numpy` in this initial benchmark step.
  - HTTP downloading for sample datasets: Handled by standard library `urllib.request` or dev dependency `httpx`.

---

## Section F: Risks and Blockers

| Domain | Risk / Blocker Identified | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Android Taxonomy Gap** | Android `ReportCategory` lacks a dedicated `STREETLIGHT` chip (users report under `INFRASTRUCTURE` or `NOT_SURE`). | Low | Does not block backend evaluation. The backend and dashboard explicitly support `"Streetlight"`. Maintain `"Streetlight"` in the 6-class benchmark. |
| **Filename Invariance in Baseline** | `PrototypeVisionAnalyzer` has `AI_ENABLE_FILENAME_HEURISTICS=False` by default. Real benchmark images with neutral UUID filenames will predict `"Other"` (0.50 confidence) in vision analysis. | Low | **Expected behavior**: Demonstrates true heuristic baseline performance. Text analysis will drive category if keywords match; otherwise, the pipeline will properly abstain (`review_required=True`). This establishes the honest quantitative gap a neural model must close. |
| **Boston 311 Image URL Volatility** | Citizen-uploaded photos in Boston 311 may experience dead links, S3 403/404 errors, or connection rate limits. | Medium | Download a small, verified sample buffer (e.g. 70 images) and keep only the first 50 verified, decoded, non-corrupt images. |
| **Consecutive Video Frame Leakage** | RDD2022 contains sequential dashcam video frames where frame $N$ and $N+1$ look identical. | Medium | Apply 64-bit perceptual hashing (`dHash`) with a strict Hamming distance threshold ($\le 4$) during curation to filter out redundant near-identical frames. |
| **TACO Context Variance** | Some TACO images depict a single bottle cap in sand rather than an actionable municipal garbage accumulation. | Low | Filter TACO candidate images by annotation area fraction ($\ge 5\%$ of image area) or multiple waste annotations per image to ensure realistic civic relevance. |
| **Existing Test Health** | None. All 88 backend tests pass cleanly in 2.30s, Ruff passes across all files, and Mypy reports 0 issues in 96 files. | None | All evaluation tooling will run in an isolated test harness without modifying existing unit/integration tests. |

---

## Section G: Recommended Implementation Order for Phase 3.2

Following this audit, Phase 3.2 should proceed in the following disciplined, sequential stages:

```
[Step 1: Repository Audit]  ◄── (COMPLETED BY THIS REPORT)
           │
           ▼
[Step 2: Scaffold Evaluation Infrastructure]
  - Create backend/app/evaluation/ (schema.py, evaluator.py, metrics.py)
  - Create datasets/ directory layout with .gitignore
           │
           ▼
[Step 3: Build Curation & Deduplication Scripts]
  - Create scripts/datasets/deduplicate.py (pure-Python dHash/pHash)
  - Create scripts/datasets/download_sample_data.py (selective 50/class downloader)
  - Create scripts/datasets/build_benchmark.py (compiles 300-sample JSONL)
           │
           ▼
[Step 4: Execute Controlled Mini-Acquisition]
  - Acquire 50 Pothole + 50 Road Damage (RDD2022 India)
  - Acquire 50 Garbage (TACO outdoor)
  - Acquire 50 Water Leakage + 50 Streetlight (Boston 311 / Roboflow)
  - Acquire 50 Other (Clean road / non-defect municipal scenes)
  - Validate magic bytes, dimensions, and deduplicate (300 clean samples total)
           │
           ▼
[Step 5: Run Baseline Evaluation]
  - Execute 300 samples through OfflineDeterministicEvaluator
  - Calculate true Macro-F1, per-class metrics, 6x6 confusion matrix, and latency
  - Write BASELINE_EVALUATION_REPORT.md (zero fabricated numbers)
           │
           ▼
[Step 6: Review Baseline & Plan Lightweight ML]
  - Inspect confusion matrix to determine where deterministic heuristics fail
  - Plan Phase 3.3 (MobileCLIP / lightweight embedding evaluation)
```
