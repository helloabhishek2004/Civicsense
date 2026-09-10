# CivicSense Backend API

The FastAPI backend powering **CivicSense — From Citizen Reports to Civic Intelligence**.

## Technology Stack

- **Framework**: FastAPI (Python 3.12+)
- **Validation**: Pydantic v2
- **ORM & Database**: SQLAlchemy 2.0, PostgreSQL 16 (psycopg 3 driver)
- **Migrations**: Alembic
- **Testing**: pytest, pytest-asyncio, httpx
- **Linting & Typing**: Ruff, mypy (strict mode)

## Directory Structure

```text
backend/
├── app/
│   ├── api/             # HTTP route handlers and dependencies
│   ├── core/            # Configuration, structured logging, centralized errors
│   ├── db/              # SQLAlchemy Base and SessionLocal
│   ├── models/          # SQLAlchemy 2.0 mapped database models
│   ├── repositories/    # Clean data access layer
│   ├── schemas/         # Pydantic validation schemas
│   ├── services/        # Domain business logic and AI service interfaces
│   └── main.py          # FastAPI application factory
├── alembic/             # Database migration scripts
├── tests/               # Automated test suite (smoke, unit, integration)
├── Dockerfile           # Minimal container definition
└── pyproject.toml       # Python packaging and tool configuration
```

## Quickstart (Local Development)

### 1. Install Dependencies

In PowerShell:
```powershell
cd backend
python -m pip install -e ".[dev]"
```

### 2. Environment Variables

Copy `.env.example` to `.env`:
```powershell
cp ../.env.example .env
```

### 3. Run Automated Tests

The test suite utilizes in-memory SQLite isolation and can run immediately without Docker:
```powershell
python -m pytest tests -v
```

### 4. Run Linting and Type Checking

```powershell
python -m ruff check app tests
python -m ruff format --check app tests
python -m mypy app
```

### 5. Start the Development Server

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API Root: `http://localhost:8000`
- Health Check: `http://localhost:8000/health`
- OpenAPI Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database Migrations (PostgreSQL)

When running local PostgreSQL (e.g. via Docker Compose):
```powershell
# Apply migrations to latest head
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Implementation Status

- **IMPLEMENTED**:
  - Full report ingestion (`POST /api/v1/reports`) starting in `SUBMITTED` state
  - Report retrieval (`GET /api/v1/reports`, `GET /api/v1/reports/{id}`)
  - Report lifecycle state machine (`ReportLifecycleManager`)
  - Domain models (`Report`, `Issue`, `Evidence`, `ModelVersion`, `AIAnalysis`, `Verification`, `Resolution`)
  - Centralized structured logging with `X-Request-ID` propagation
  - Unified error response format
  - Abstract AI service interfaces raising `NotImplementedError`
- **PLANNED**:
  - Vision detection & classification model inference (Sprint 3)
  - Text analytics & safety extraction (Sprint 4)
  - Multimodal fusion & agreement scoring (Sprint 5)
  - Geospatial clustering & duplicate grouping (Sprint 5)
  - Human review queue orchestration (Sprint 6)
  - Spatial analytics & pattern mining (Sprint 7)
