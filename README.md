# CivicSense — From Citizen Reports to Civic Intelligence

**CivicSense** is an AI-assisted civic decision-support and intelligence platform that bridges citizen defect reporting with municipal operational response. It combines privacy-preserving mobile preprocessing, server-side multimodal reasoning, separate severity and priority assessment, human-in-the-loop verification, and historical data mining.

---

## 1. Current Development Stage: Phase 0 (Bootstrap Foundation)

> [!IMPORTANT]
> This repository is currently in **Phase 0: Initial Production Codebase Bootstrap**.
> We have built a clean, scalable, typed production foundation. Heavy ML dependencies, custom deep learning models, vector databases, and external cloud services are **deliberately NOT installed or implemented yet** to prevent premature complexity.

| Status | Component | Notes |
| :--- | :--- | :--- |
| **IMPLEMENTED** | Backend Ingestion API | FastAPI versioned routes, request validation, structured error handling |
| **IMPLEMENTED** | Report Lifecycle Engine | 11-state transition machine (`SUBMITTED` $\dots$ `CLOSED`) |
| **IMPLEMENTED** | Database & Migrations | PostgreSQL 16 + SQLAlchemy 2.0 + Alembic (`0001_initial`) |
| **IMPLEMENTED** | Clean Domain Models | `Report`, `Issue`, `Evidence`, `ModelVersion`, `AIAnalysis`, `Verification`, `Resolution` |
| **IMPLEMENTED** | AI Service Contracts | Explicit interfaces raising `NotImplementedError` (Zero fake AI) |
| **IMPLEMENTED** | Mobile Scaffolding | React Native + Expo + TypeScript strict mode + typed API client |
| **IMPLEMENTED** | Shared Contract | Canonical JSON Schema (`shared/schemas/report_submission.json`) |
| **IMPLEMENTED** | Developer Tooling | PowerShell (`scripts/dev.ps1`), Bash (`scripts/dev.sh`), Makefile, Ruff, mypy, pytest |
| **PLANNED** | Vision Inference | Server-side & edge lightweight visual classification (Sprint 3) |
| **PLANNED** | Text Analytics | Context & safety hazard extraction from citizen text (Sprint 4) |
| **PLANNED** | Multimodal Fusion | Feature fusion & agreement/conflict detection (Sprint 5) |
| **PLANNED** | Duplicate Grouping | Geospatial proximity + vector similarity grouping (Sprint 5) |
| **PLANNED** | Human Verification UI | Reviewer interface for ambiguous/critical cases (Sprint 6) |
| **PLANNED** | Civic Data Mining | Spatial clustering, recurring defect patterns, temporal trends (Sprint 7) |
| **PLANNED** | Authority Dashboard | Web management dashboard with GIS mapping (Sprint 7) |

---

## 2. Core Architectural Principles

1. **`Report != Issue`**: An individual submission from a citizen is a `Report`. An underlying real-world civic problem on the ground is an `Issue`. Multiple reports can map to one issue.
2. **`Confidence != Severity != Priority`**:
   - `Confidence`: Model's statistical certainty in its categorization.
   - `Severity`: Physical seriousness or structural risk of the defect.
   - `Priority`: Urgency of administrative response, calculated from severity, recurrence, safety indicators, and location.
3. **`Evidence Preservation`**: Raw images and text are never discarded in favor of embeddings. Original evidence remains retrievable for human verification and legal audits.
4. **`Prediction != Decision`**: AI outputs are preliminary evidence; the Decision Engine decides whether a case proceeds automatically or routes to human review.
5. **`Model Provenance`**: Every future AI result records its `model_name`, `model_version`, `preprocessing_version`, and `embedding_model`.

---

## 3. Repository Structure

```text
Civicsense/
├── .env.example              # Documented environment variables template
├── docker-compose.yml        # Local PostgreSQL 16 infrastructure
├── Makefile                  # Cross-platform developer commands
├── README.md                 # Project documentation and guide
│
├── docs/                     # Architecture overviews, API contracts, ADRs, and research
│   ├── architecture/         # System diagrams and status mappings
│   ├── api/                  # REST API reference
│   ├── decisions/            # Architectural Decision Records (e.g. ADR-001)
│   └── research/             # Academic research questions and evaluation plans
│
├── shared/
│   └── schemas/              # Versioned client-server JSON Schema contracts
│
├── backend/                  # FastAPI Application
│   ├── app/                  # Application core, api, models, repos, services, db
│   ├── alembic/              # Database migrations
│   ├── tests/                # Automated pytest suite (smoke, unit, integration)
│   └── pyproject.toml        # Dependencies, Ruff, mypy, pytest configs
│
├── mobile/                   # React Native Expo Mobile App
│   ├── src/                  # Core api/config, features/reports, shared components
│   ├── App.tsx               # Application root
│   └── package.json          # Dependencies and scripts
│
├── ml/                       # Future ML experimentation workspace
│   ├── datasets/             # Public dataset manifests (RDD2022, TACO)
│   ├── preprocessing/        # Image and text preprocessing
│   ├── training/             # Model training pipelines
│   └── evaluation/           # Benchmarks and evaluation harnesses
│
├── dashboard/                # Future authority dashboard placeholder
└── scripts/                  # Cross-platform development scripts (dev.ps1, dev.sh)
```

---

## 4. Technology Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 16 (`psycopg` 3)
- **Mobile**: React Native, Expo SDK 52, TypeScript (strict mode)
- **Code Quality**: Ruff (linting & formatting), mypy (strict type checking), pytest
- **Infrastructure**: Docker Compose (PostgreSQL)

---

## 5. Quickstart Guide

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- Docker Desktop (optional, for running local PostgreSQL)

### A. Setup Environment

```powershell
# Copy environment template
cp .env.example .env
```

### B. Install Dependencies

Using PowerShell:
```powershell
.\scripts\dev.ps1 install
```

Or manually:
```powershell
# Backend
cd backend
python -m pip install -e ".[dev]"
cd ..

# Mobile
cd mobile
npm install
cd ..
```

---

## 6. Running Tests & Quality Checks

The backend test suite uses an in-memory SQLite configuration with zero external dependencies, running cleanly in milliseconds:

```powershell
# Run backend tests
.\scripts\dev.ps1 test

# Run linter and formatting checks
.\scripts\dev.ps1 lint

# Run strict type checking (mypy + tsc)
.\scripts\dev.ps1 typecheck
```

---

## 7. Running the Backend API

```powershell
.\scripts\dev.ps1 dev
```
- API Root: `http://localhost:8000`
- Liveness Probe: `http://localhost:8000/health`
- Versioned Health: `http://localhost:8000/api/v1/health`
- OpenAPI Swagger Docs: `http://localhost:8000/docs`
- ReDoc Docs: `http://localhost:8000/redoc`

---

## 8. Running the Mobile Application

```powershell
cd mobile
npm start
```
- Press `w` to launch the web client in your browser.
- Or scan the QR code with Expo Go on your physical Android or iOS device.

---

## 9. Database Management (PostgreSQL)

When running local PostgreSQL via Docker:

```powershell
# Start PostgreSQL container
.\scripts\dev.ps1 db-up

# Apply Alembic migrations
.\scripts\dev.ps1 db-migrate

# Stop PostgreSQL container
.\scripts\dev.ps1 db-down
```

---

## 10. Development Philosophy

1. **Simple > Impressive**: Prefer reliable, well-tested technologies over premature complexity.
2. **Replaceable Modules**: Vision, text, similarity, fusion, and decision engines communicate via explicit abstract interfaces.
3. **No Dead Code**: Every file serves a defined purpose; no empty fake classes.
4. **Research-Friendly**: Clear separation between transactional ingestion and analytical evaluation.
5. **No Fake AI**: Services raise `NotImplementedError` until real evaluated models are added.
