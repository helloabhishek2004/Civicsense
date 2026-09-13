# CivicSense — Deployment Guide

**Version:** 1.0.0
**Last Updated:** 2026-09-13

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12+ | Backend runtime |
| Node.js | 18+ | Dashboard build |
| Docker Desktop | Latest | PostgreSQL 16 |
| Git | Latest | Repository |

---

## 1. Environment Variables

### Backend (`backend/.env`)

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/civicsense
API_ENV=development
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
MAX_PAYLOAD_SIZE_BYTES=10485760
```

### Dashboard (`dashboard/.env`)

```env
VITE_DATA_MODE=api
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_GOOGLE_MAPS_API_KEY=your-key-here
```

---

## 2. Backend Startup

```powershell
# Install dependencies
cd backend
python -m pip install -e ".[dev]"

# Apply migrations
python -m alembic upgrade head

# Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Verify:** `curl http://localhost:8000/health`

---

## 3. Dashboard Startup

```powershell
cd dashboard
npm install
npm run dev
```

**Open:** `http://localhost:5173`

---

## 4. Database Setup

### PostgreSQL (Production)

```powershell
# Start PostgreSQL
docker compose up -d

# Apply migrations
cd backend
python -m alembic upgrade head

# Seed pilot data (optional)
python scripts/seed_pilot_dataset.py --seed-db
```

### SQLite (Testing Only)

The test suite uses in-memory SQLite automatically. No setup required.

```powershell
cd backend
python -m pytest tests -v
```

---

## 5. MiniLM Model

The similarity engine requires the `all-MiniLM-L6-v2` model.

```powershell
# Model should be at:
models/all_minilm_l6_v2/

# If missing, the backend starts in degraded mode (no embeddings)
# Download from HuggingFace:
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2').save('models/all_minilm_l6_v2')"
```

---

## 6. CORS Configuration

Backend accepts requests from:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (alternative)
- `http://localhost:8081` (Expo)
- `http://localhost:19006` (Expo web)
- Regex: `^https?://(localhost|127\.0\.0\.1)(:\d+)?$`

---

## 7. Seed Process

```powershell
# Export to JSON (no database needed)
python scripts/seed_pilot_dataset.py --export-only

# Seed database (idempotent, skips duplicates)
python scripts/seed_pilot_dataset.py --seed-db

# Reset and re-seed (destructive)
python scripts/seed_pilot_dataset.py --seed-db --reset
```

**Expected output:** 40 reports, 12 issues, 10 matches (6 pending, 4 rejected)

---

## 8. Health Verification

```powershell
# Basic health
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "ok",
#   "database": "healthy",
#   "models": {"minilm": "READY", "degraded_mode": false},
#   "pending_candidate_matches": 6
# }
```

---

## 9. PostgreSQL Requirement

**Production target:** PostgreSQL 16

The test suite runs on SQLite for speed, but production requires PostgreSQL for:
- UUID native type
- JSONB columns
- Enum handling
- Transaction isolation
- Concurrent match review protection

### Smoke Test

```powershell
# Start PostgreSQL
docker compose up -d

# Set DATABASE_URL
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/civicsense"

# Run smoke test
cd backend
python -m alembic upgrade head
python -m scripts.smoke_test_postgres
```

---

## 10. Prototype Authentication Warning

> **NOT PRODUCTION AUTHENTICATION**
>
> The current `X-Reviewer-ID` header mechanism is prototype-only.
> It accepts any non-empty string without verification.
>
> **Production requires:**
> - JWT or session-based authentication
> - Role-based access control (RBAC)
> - Server-side authorization checks
> - Secure credential management

---

## 11. Production Hardening Requirements

Before public/external deployment:

| Priority | Item |
|---|---|
| P0 | Real authentication (JWT/RBAC) |
| P0 | PostgreSQL validation |
| P0 | Rate limiting |
| P0 | Input abuse protection |
| P0 | HTTPS and secure CORS |
| P0 | Secrets management (not .env files) |
| P0 | Audit security |
| P0 | Privacy policy / data retention |
| P0 | Monitoring and alerting |
| P0 | Backup/recovery |
| P1 | Browser E2E tests |
| P1 | Better reviewer UX |
| P1 | Structured explainability |
| P1 | Real-world evaluation dataset |
| P1 | Error monitoring |
| P2 | Image classification |
| P2 | Advanced geospatial clustering |
| P2 | Notifications |
| P2 | Citizen tracking |
| P2 | Multilingual support |

---

## 12. Quick Reference

```powershell
# Full local setup
docker compose up -d
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/civicsense"
cd backend; python -m alembic upgrade head; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd dashboard; npm run dev

# Run all tests
cd backend; python -m pytest tests -q
cd dashboard; npm test -- --run

# Seed and verify
python scripts/seed_pilot_dataset.py --seed-db --reset
curl http://localhost:8000/health
```
