# CivicSense — Implementation Memory

## 1. Project Architecture

The current high-level system architecture is a monorepo consisting of:

- **Citizen Mobile Application**: React Native + Expo (TypeScript strict mode).
- **Backend API**: Python FastAPI service providing versioned REST endpoints (`/api/v1/`).
- **Relational Database**: PostgreSQL 16 managed via SQLAlchemy 2.0 ORM and Alembic migrations.
- **Shared Contracts**: Canonical JSON Schemas governing client-to-server payloads.
- **Service Interfaces**: Abstract interfaces for future vision, text, fusion, similarity, decision, and analytics modules (raising `NotImplementedError`; no fake AI).
- **Developer Orchestration**: Docker Compose for local database infrastructure, accompanied by PowerShell (`scripts/dev.ps1`), Bash (`scripts/dev.sh`), and `Makefile` task runners.

---

## 2. Applications

### Mobile Client (React Native / Expo)

**Status:** Implemented (Phase 0 Scaffold)

- Built with Expo SDK 52 and React Native in strict TypeScript mode.
- Feature-oriented directory structure (`mobile/src/features/reports/`, `mobile/src/core/`, `mobile/src/shared/`).
- `ApiClient`: Typed HTTP client with configurable `EXPO_PUBLIC_API_BASE_URL`, request timeout handling via `AbortController`, client-side `X-Request-ID` generation, and structured API error parsing.
- `ReportCreateScreen`: Validates citizen problem description (minimum 3 characters), displays attached GPS coordinates via `LocationPickerStub`, displays attached evidence placeholder, and executes submission.
- `ReportDetailScreen`: Displays tracking ID, lifecycle status badge, coordinates, description, and timeline.
- State-driven navigation in `App.tsx` between submission and detail views.

### Web Dashboard

**Status:** Not Implemented

- Directory placeholder created at `dashboard/`. No frontend framework or dashboard code installed yet.

---

## 3. Backend

**Status:** Implemented (Phase 0 Foundation)

- **Framework**: FastAPI (Python 3.12+) with Pydantic v2 validation.
- **Layered Architecture**: Route handlers (`app/api/`) $\to$ Pydantic schemas (`app/schemas/`) $\to$ Domain services (`app/services/`) $\to$ Data access repositories (`app/repositories/`) $\to$ SQLAlchemy ORM models (`app/models/`).
- **Request Tracing**: `RequestContextMiddleware` generates or propagates `X-Request-ID` on every request, binds it to `contextvars`, and includes it in all response headers.
- **Structured Logging**: `CivicSenseLogFormatter` injects timestamp, log level, service name, and `request_id` into all stdout logs without logging sensitive user credentials, tokens, or raw image binaries.
- **Standardized Error Handling**: Global exception handlers format all 4xx/5xx errors into a unified structure (`{"error": {"code": "...", "message": "...", "request_id": "...", "details": []}}`).
- **Endpoints Implemented**:
  - `GET /health` & `GET /api/v1/health`: API liveness probes.
  - `GET /docs` & `GET /redoc`: Interactive OpenAPI documentation.
  - `POST /api/v1/reports`: Ingests citizen report, assigns human-readable tracking ID (`REP-YYYYMM-XXXXXX`), initializes status to `SUBMITTED`, persists attached evidence references, and returns 201 Created.
  - `GET /api/v1/reports`: Paginated list of reports sorted descending by creation time.
  - `GET /api/v1/reports/{id}`: Retrieves single report by internal UUID or tracking ID.
- **Report Lifecycle Engine**: `ReportLifecycleManager` enforces valid transitions across 11 explicit states (`SUBMITTED`, `AI_PROCESSING`, `AI_PROCESSED`, `VERIFICATION_REQUIRED`, `VERIFIED`, `PRIORITIZED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `RESOLUTION_VERIFIED`, `CLOSED`). `CLOSED` is enforced as a terminal state.

---

## 4. Database

**Status:** Implemented (Schema & Migrations)

- **Engine & Dialect**: PostgreSQL 16 (psycopg 3 driver) with fallback compatibility for SQLite in isolated automated tests.
- **ORM**: Modern SQLAlchemy 2.0 with strict `Mapped[T]` and `mapped_column()` typing.
- **Migrations**: Alembic with initial migration `0001_initial_civicsense_schema.py` creating complete schema, foreign keys, and indexes.
- **Core Entities & Schema Decisions**:
  - **`Report != Issue`**: `Report` represents an individual citizen submission. `Issue` represents a real-world civic defect on the ground. Multiple reports can map to one issue via foreign key `reports.issue_id`.
  - **Primary Keys**: Internal database IDs use native `UUID`. Citizen-facing tracking IDs are stored separately as unique indexed strings (`tracking_id`).
  - **Evidence Preservation**: `evidences` table stores raw asset metadata (`evidence_type`, `storage_uri`, `file_hash`, `mime_type`, `file_size_bytes`, `metadata_json`). Original evidence is preserved and not discarded when representations are generated.
  - **Model Provenance**: `model_versions` table records `model_name`, `model_version`, `preprocessing_version`, `embedding_model`, and `embedding_version`.
  - **Decoupled AI Outputs**: `ai_analyses` table keeps `confidence`, `severity` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `priority` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and `evidence_agreement` in separate independent columns (no monolithic "ai_score").
  - **Audit Tables**: `verifications` records human review verdicts (`CONFIRMED`, `CORRECTED`, `REJECTED`, `DUPLICATE`). `resolutions` records municipal repair completion on an `Issue` without deleting historical defect records.

---

## 5. AI / ML Pipeline

**Status:** Not Implemented (Interfaces Only)

- No ML frameworks (PyTorch, Ultralytics, Transformers, OpenCV) or model weights are installed in Phase 0.
- Honest abstract service interfaces exist:
  - `IVisionService`: Image inference and feature extraction contracts (raises `NotImplementedError`).
  - `ITextService`: Text classification and embedding contracts (raises `NotImplementedError`).
  - `IFusionService`: Multimodal feature fusion and agreement/conflict detection contracts (raises `NotImplementedError`).
  - `ISimilarityService`: Duplicate detection and nearest neighbor search contracts (raises `NotImplementedError`).
  - `IDecisionService`: Severity, priority, and human review routing contracts (raises `NotImplementedError`).
  - `IVerificationService`: Human verification routing and verdict processing contracts (raises `NotImplementedError`).
  - `IAnalyticsService`: Hotspot clustering and frequent pattern mining contracts (raises `NotImplementedError`).

---

## 6. Edge / On-Device Processing

**Status:** Not Implemented

- Mobile client currently captures text descriptions and GPS coordinates as input data. On-device image preprocessing, quality estimation, and lightweight local ML runtimes (ONNX/LiteRT) are deferred to subsequent sprints.

---

## 7. Data / Analytics

**Status:** Not Implemented

- No spatial clustering, frequent pattern mining (Apriori/FP-Growth), or temporal trend models are implemented yet.

---

## 8. MLOps

**Status:** Foundation Only

- Database schema supports model provenance linking (`ModelVersion` table linked to `AIAnalysis`).
- Automated retraining pipelines, model registries (MLflow), and data versioning (DVC) are not installed or implemented yet.

---

## 9. Major Architectural Changes

- **Bootstrap Phase 0**: Established the initial monorepo foundation. Explicitly enforced domain separations (`Report != Issue`, `Confidence != Severity != Priority`, `Prediction != Decision`, `Evidence != Representation`). Prohibited synthetic/mock AI logic in favor of strict `NotImplementedError` interfaces.

---

## 10. Current Implementation State

- **Backend**: Fully functional FastAPI service with 21 passing automated tests (`pytest`), strict type checking (`mypy`), zero lint/format issues (`ruff`), and verified live HTTP socket smoke tests.
- **Database**: PostgreSQL 16 Docker Compose configuration and complete initial Alembic migration.
- **Mobile**: React Native + Expo client with zero TypeScript compiler errors (`tsc --noEmit`), typed API client, and report submission/detail UI.
- **Contracts**: Shared JSON schema (`shared/schemas/report_submission.json`) defining the edge-to-cloud report submission contract.
