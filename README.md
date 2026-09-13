# CivicSense — From Citizen Reports to Civic Intelligence

**CivicSense** is an AI-assisted civic decision-support and intelligence platform that bridges citizen defect reporting with municipal operational response. It combines text semantic similarity, geospatial proximity analysis, human-in-the-loop match review, dynamic priority ranking, and departmental workflow orchestration.

---

## 1. Current Status

| Component | Status | Tests |
| :--- | :--- | :--- |
| **Backend API** | IMPLEMENTED | 470 passing |
| **Similarity & Dedup Engine** | IMPLEMENTED | 67 unit + 21 API tests |
| **Priority Ranking Engine** | IMPLEMENTED | 53 tests |
| **Issue Management API** | IMPLEMENTED | 5 endpoint tests |
| **Match Review Workflow** | IMPLEMENTED | 38 tests |
| **Department Operations** | IMPLEMENTED | Tested |
| **Web Dashboard** | IMPLEMENTED | 85 passing |
| **Android Mobile App** | IMPLEMENTED | 76 passing |
| **React Native Expo** | SCAFFOLD | — |
| **Image Classification** | PILOT ONLY | Not integrated |
| **Production Auth** | NOT IMPLEMENTED | Prototype X-Reviewer-ID only |

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
├── .env.example              # Environment variables template
├── docker-compose.yml        # PostgreSQL 16 infrastructure
├── Makefile                  # Cross-platform developer commands
├── README.md                 # This file
│
├── docs/                     # Architecture, API, deployment, demo docs
│   ├── ARCHITECTURE.md       # System architecture, component status, and Mermaid diagram
│   ├── API.md                # REST API reference with 29 endpoints
│   ├── DEPLOYMENT.md         # Setup and deployment guide
│   ├── DEMO_RUNBOOK.md       # Demo scenario and navigation guide
│   ├── AI_EVALUATION.md      # AI methodology and evaluation
│   ├── PROJECT_OVERVIEW.md   # Project summary and workflow
│   ├── PROBLEM_STATEMENT.md  # Problem definition and motivation
│   ├── SYSTEM_OBJECTIVES.md  # System design objectives
│   ├── METHODOLOGY.md        # Technical methodology
│   ├── RESULTS_AND_LIMITATIONS.md # Test results and limitations
│   ├── PRESENTATION_OUTLINE.md    # 12-slide presentation structure
│   ├── PRESENTATION_DEMO_SCRIPT.md # 5-8 min live demo script
│   ├── PORTFOLIO_DESCRIPTION.md   # Portfolio-ready summary
│   ├── architecture/         # System diagrams
│   ├── api/                  # API reference (legacy)
│   └── decisions/            # Architectural Decision Records
│
├── backend/                  # FastAPI Application
│   ├── app/                  # Application core, api, models, services
│   ├── alembic/              # Database migrations (0001-0010)
│   ├── tests/                # 470 passing pytest tests
│   └── pyproject.toml        # Dependencies and tool config
│
├── dashboard/                # React + Vite Admin Portal
│   ├── src/                  # Components, features, services
│   └── package.json          # Dependencies and scripts
│
├── android/                  # Native Android (Kotlin + Compose)
├── mobile/                   # React Native Expo scaffold
├── models/                   # MiniLM model artifacts
├── scripts/                  # Dev scripts, seed, evaluation tools
│   ├── seed_pilot_dataset.py # Pilot data seeding
│   └── smoke_test_postgres.py# PostgreSQL smoke test
└── datasets/                 # Evaluation benchmarks and pilot data
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
- Docker Desktop (for PostgreSQL 16)

### A. Setup Environment

```powershell
# Copy environment template
cp .env.example .env
```

### B. Start PostgreSQL

```powershell
docker compose up -d
```

### C. Install Dependencies

```powershell
# Backend
cd backend
python -m pip install -e ".[dev]"

# Dashboard
cd ../dashboard
npm install
```

### D. Apply Migrations

```powershell
cd backend
python -m alembic upgrade head
```

### E. Seed Pilot Data (Optional)

```powershell
python scripts/seed_pilot_dataset.py --seed-db
```

### F. Start Services

```powershell
# Terminal 1: Backend
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Dashboard
cd dashboard
npm run dev
```

### G. Open Dashboard

Navigate to `http://localhost:5173`

- Login with any badge number (prototype auth)
- Go to AI Operations → Candidate Duplicate Reviews tab
- See 6 pending candidate matches from the pilot dataset

---

## 6. Running Tests & Quality Checks

```powershell
# Backend tests (470 passing, in-memory SQLite)
cd backend
python -m pytest tests -q

# Backend linting
python -m ruff check app --select=E,W,F,I --ignore=E501

# Frontend tests (85 passing)
cd ../dashboard
npm test -- --run

# Frontend type check
npm run typecheck

# Frontend build
npm run build
```

---

## 7. API Documentation

- **Interactive Swagger:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **API Reference:** See `docs/API.md`

**Key endpoints:**
- `GET /health` — System health check
- `POST /api/v1/reports` — Submit citizen report
- `GET /api/v1/reports` — List reports (filterable by issue_id)
- `GET /api/v1/issues` — List issues sorted by priority
- `GET /api/v1/matches/pending` — Pending candidate matches
- `POST /api/v1/matches/{id}/approve` — Approve match (requires X-Reviewer-ID)
- `POST /api/v1/matches/{id}/reject` — Reject match (requires X-Reviewer-ID)

---

## 8. Demo

See `docs/DEMO_RUNBOOK.md` for:
- Step-by-step demo scenarios
- Navigation instructions
- Expected outcomes
- Reset and troubleshooting

---

## 9. Documentation

| Document | Purpose |
|---|---|
| `docs/ARCHITECTURE.md` | System architecture, component status, and Mermaid diagram |
| `docs/API.md` | REST API reference with 29 endpoints |
| `docs/DEPLOYMENT.md` | Setup and deployment guide |
| `docs/DEMO_RUNBOOK.md` | Demo scenarios and navigation |
| `docs/AI_EVALUATION.md` | AI methodology and evaluation metrics |
| `docs/PROJECT_OVERVIEW.md` | Project summary, technologies, workflow |
| `docs/PROBLEM_STATEMENT.md` | Problem definition and motivation |
| `docs/SYSTEM_OBJECTIVES.md` | System design objectives and requirements |
| `docs/METHODOLOGY.md` | Technical methodology and implementation status |
| `docs/RESULTS_AND_LIMITATIONS.md` | Test results, evaluation, and known limitations |
| `docs/PRESENTATION_OUTLINE.md` | 12-slide presentation structure |
| `docs/PRESENTATION_DEMO_SCRIPT.md` | 5-8 minute live demo script |
| `docs/PORTFOLIO_DESCRIPTION.md` | Portfolio-ready project summary |
| `memory.md` | Implementation memory and current state |
| `AGENTS.md` | Agent operating guidelines |
