# Contributing to CivicSense

Thank you for your interest in CivicSense! This document explains how to contribute effectively.

> By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Table of Contents

- [Ways to Contribute](#ways-to-contribute)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Branching & Commit Convention](#branching--commit-convention)
- [Pull Request Process](#pull-request-process)
- [Code Quality Requirements](#code-quality-requirements)
- [Testing Requirements](#testing-requirements)
- [Architecture Principles](#architecture-principles)
- [Adding a New Civic Category](#adding-a-new-civic-category)

---

## Ways to Contribute

| Type | Description |
|------|-------------|
| 🐛 **Bug reports** | Open an issue using the Bug Report template |
| 💡 **Feature requests** | Open an issue using the Feature Request template |
| 📝 **Documentation** | Fix typos, improve explanations, add examples |
| 🧪 **Tests** | Add missing tests, improve coverage |
| 🤖 **ML / datasets** | Improve model accuracy, contribute annotated data, report ML issues |
| 🔧 **Code** | Fix bugs, implement features from open issues |

For large or uncertain changes, **open an issue first** and discuss before investing time in code.

---

## Development Setup

### Prerequisites

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| Git | 2.40+ | Version control |
| Python | 3.11+ | Backend |
| Node.js | 20 LTS | Dashboard & mobile scaffold |
| Docker Desktop | 24+ | PostgreSQL database |
| Android Studio | Ladybug (2024.2+) | Android app |
| JDK | 21 | Android Gradle |

### 1. Fork and clone

```bash
git clone https://github.com/<your-username>/Civicsense.git
cd Civicsense
git remote add upstream https://github.com/helloabhishek2004/Civicsense.git
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL
```

For the dashboard:
```bash
cp dashboard/.env.example dashboard/.env 2>/dev/null || true
# Set VITE_DATA_MODE=mock for local development without a running backend
```

For the Android app:
```bash
cp android/local.properties.example android/local.properties
# Set MAPS_API_KEY=<your-key> and API_BASE_URL=http://10.0.2.2:8000
```

### 3. Start the database

```bash
docker compose up -d
```

### 4. Set up the backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 5. Set up the dashboard

```bash
cd dashboard
npm install
npm run dev        # http://localhost:5173
```

### 6. Set up the Android app

Open `android/` in Android Studio → sync Gradle → run on emulator or device.

Or via command line:
```bash
cd android && ./gradlew assembleDebug
```

---

## Project Structure

```
android/        — Kotlin + Jetpack Compose native app
backend/        — FastAPI Python backend + Alembic migrations
dashboard/      — React + Vite TypeScript web dashboard
mobile/         — React Native / Expo scaffold (Phase 0)
ml/             — ML training and evaluation scripts
datasets/       — Benchmark datasets and evaluation runs
shared/         — JSON schemas shared by all clients
docs/           — Architecture, API, deployment documentation
scripts/        — Developer utilities
```

---

## Branching & Commit Convention

### Branch names

```
feature/<short-description>     # New functionality
fix/<short-description>         # Bug fixes
docs/<short-description>        # Documentation only
test/<short-description>        # Tests only
ml/<short-description>          # ML / data changes
chore/<short-description>       # Build, tooling, deps
```

### Commit messages — Conventional Commits

```
<type>(<scope>): <imperative summary>

[optional body]

[optional footer: Fixes #123]
```

**Types:** `feat` · `fix` · `docs` · `test` · `chore` · `ml` · `refactor` · `perf`

**Scopes:** `android` · `backend` · `dashboard` · `mobile` · `ml` · `db` · `ci` · `docs`

**Examples:**
```
feat(android): add pull-to-refresh on MyReportsScreen
fix(backend): prevent duplicate issue creation under concurrent submissions
docs(api): document /reports/{id} response shape
ml(vision): add augmentation pipeline for low-light civic images
```

---

## Pull Request Process

1. Sync your fork: `git fetch upstream && git rebase upstream/master`
2. Create a branch from `master`
3. Make your changes — keep PRs small and focused
4. Ensure all checks pass locally (see [Testing Requirements](#testing-requirements))
5. Push to your fork and open a PR against `master`
6. Fill in the PR template completely
7. A maintainer will review within a reasonable time — be patient

**PRs that will be declined without review:**
- PRs that silence linting/type errors without fixing them
- PRs that skip tests or break existing tests
- PRs that contain committed secrets, credentials, or personal data
- Very large PRs that change unrelated systems simultaneously

---

## Code Quality Requirements

### Python (backend, ml/)

```bash
cd backend
ruff check .        # Linting
mypy .              # Type checking — strict mode
```

- No `print()` statements in production paths — use structured logging
- All new public functions must have type annotations
- No bare `except:` clauses
- Pydantic v2 models for all request/response schemas

### TypeScript (dashboard, mobile/)

```bash
cd dashboard
npx tsc --noEmit    # Type check
npm run lint        # ESLint
```

- Strict TypeScript — no `any` without explicit justification
- No `console.log` in production paths
- Components must handle loading, error, and empty states

### Kotlin (android/)

```bash
cd android
./gradlew lintDebug
```

- No `Log.d` or `println` in production code paths (use the structured diagnostic tags defined per-feature)
- All coroutines must handle exceptions via `try/catch/finally`
- No hardcoded IP addresses or API keys in source files

---

## Testing Requirements

Before submitting a PR, all existing tests must pass and new functionality must be covered:

```bash
# Backend
cd backend && pytest -v

# Dashboard
cd dashboard && npm test -- --run

# Android unit tests
cd android && ./gradlew testDebugUnitTest

# Dashboard build check
cd dashboard && npm run build
```

**Coverage expectations:**
- New backend service methods → pytest unit tests
- New dashboard components with business logic → Vitest tests
- New Android ViewModel/Repository logic → JUnit4 tests
- ML pipeline changes → evaluation scripts in `ml/` with results committed to `datasets/evaluation_runs/`

---

## Architecture Principles

These are non-negotiable design rules. PRs that violate them will be asked to revise.

### Report ≠ Issue
A `Report` is a single citizen submission event. An `Issue` is a deduplicated real-world defect that may be linked to multiple reports. **Never conflate them in models, schemas, or UI language.**

### Confidence ≠ Severity ≠ Priority
These three fields are computed independently by separate heuristics. They are always displayed and stored as separate fields. Never derive one from another without explicit, justified logic.

### No fake AI
AI outputs are probabilistic estimates, never ground truth. The system supports explicit uncertainty states (`UNKNOWN`, `OTHER`, `REVIEW_REQUIRED`, `LOW_CONFIDENCE`, `CONFLICTING_EVIDENCE`). Never force an ambiguous input into a definite category.

### Human verification is mandatory
AI classification results must go through human verification (`VERIFIED` / `CORRECTED` / `REJECTED`) before influencing any operational workflow. Never auto-apply AI decisions.

### No business logic in controllers
Validation and business rules belong in `services/`. Database queries belong in `repositories/`. API routes are thin coordinators only.

---

## Adding a New Civic Category

1. Add the category to `shared/schemas/report.schema.json`
2. Add the backend enum in `backend/app/models/enums.py`
3. Add a new Alembic migration if the database enum changes
4. Add the Android `ReportCategory` enum value in `android/.../ReportCategory.kt`
5. Add at least 20 labeled examples to the benchmark dataset in `datasets/benchmark_v1/`
6. Re-run the evaluation pipeline and commit results to `datasets/evaluation_runs/`
7. Update `docs/ARCHITECTURE.md` with the new category
