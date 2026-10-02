<div align="center">

<img src="android/app/src/main/res/drawable/ic_civicsense_path_logo.xml" width="72" alt="CivicSense logo" />

# CivicSense

**Citizen-to-Municipality Issue Reporting with AI-Assisted Triage**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Android](https://img.shields.io/badge/Android-Kotlin%20%7C%20Compose-3DDC84?logo=android)](android/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.11-009688?logo=fastapi)](backend/)
[![Dashboard](https://img.shields.io/badge/Dashboard-React%20%7C%20TypeScript-61DAFB?logo=react)](dashboard/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?logo=postgresql)](docker-compose.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [Tech Stack](#-tech-stack) · [Contributing](#-contributing) · [License](#-license)

</div>

---

CivicSense is an open-source civic issue reporting platform that bridges citizens and municipal authorities. Citizens photograph and describe problems in their neighbourhood — potholes, broken streetlights, garbage dumping, water leaks — and the platform uses multimodal AI to classify, deduplicate, and route reports for human-verified triage.

> **Status:** Pre-production research prototype (v0.1.0). All AI outputs are estimates and subject to mandatory human verification before any operational decision is made.

---

## ✨ Features

### Citizen Android App
- Native Android (Kotlin + Jetpack Compose, Material 3)
- 4-step reporting wizard: evidence capture → description → live map location → review
- Camera capture with FileProvider, gallery picker, EXIF stripping
- Real-time report status tracking with timeline display
- Automatic silent polling (status updates every 6–10 s while app is open)
- Offline report queueing with graceful recovery
- Material 3 pull-to-refresh, expressive loading animations
- Adaptive icon, themed icon (Android 13+), high-refresh-rate support

### Authority Web Dashboard
- React 18 + TypeScript SPA with server-side data via TanStack Query
- Report queue with sortable, filterable table view
- Interactive map (Leaflet + OpenStreetMap) with issue cluster overlay
- Analytics charts (category distribution, trend lines, resolution rates)
- AI operations panel (confidence scores, embedding explorer)
- Department management and assignment workflow

### FastAPI Backend
- Versioned REST API at `/api/v1/`
- Pydantic v2 request/response validation
- 11-migration Alembic schema with strict `Report` ↔ `Issue` domain separation
- Multimodal AI pipeline: MiniLM text embeddings + MobileNetV3-Small visual embeddings
- Cosine-similarity duplicate detection and issue clustering
- Confidence, severity, and priority scores as independent fields — never conflated
- Human verification layer (AI outputs flagged, never auto-applied)
- PostgreSQL 16 via SQLAlchemy 2.0 async ORM (psycopg3)

### AI / ML Pipeline
- **Text**: MiniLM L6 v2 (384-dim sentence embeddings) for category classification and duplicate text matching
- **Vision**: MobileNetV3-Small fine-tuned on civic categories (576-dim feature embeddings)
- **Fusion**: Weighted concatenation baseline; empirically evaluated against unimodal baselines
- Benchmark dataset (`datasets/benchmark_v1/`) with 6 civic categories
- Evaluation runs with confusion matrices, latency reports, and calibration reports (`datasets/evaluation_runs/`)

---

## 🏛 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CivicSense                               │
│                                                                 │
│  ┌──────────────┐     ┌─────────────────┐    ┌──────────────┐  │
│  │ Android App  │────▶│  FastAPI Backend │◀───│ Web Dashboard│  │
│  │ (Kotlin/     │     │  /api/v1/        │    │ (React/Vite) │  │
│  │  Compose)    │     │                 │    │              │  │
│  └──────────────┘     │  ┌───────────┐  │    └──────────────┘  │
│                       │  │ AI/ML     │  │                       │
│  ┌──────────────┐     │  │ Pipeline  │  │    ┌──────────────┐  │
│  │ React Native │────▶│  │ MiniLM +  │  │    │  PostgreSQL  │  │
│  │ (Expo/RN)    │     │  │ MobNetV3  │  │───▶│     16       │  │
│  └──────────────┘     │  └───────────┘  │    └──────────────┘  │
│                       └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

**Key domain rule:** A `Report` is a single citizen submission event. An `Issue` is a deduplicated real-world defect that may be supported by multiple reports. The pipeline never merges these automatically without human confirmation.

**AI decision chain:**

```
Raw Report
    │
    ├─▶ Text Embedding (MiniLM) ─────────────────┐
    │                                            ├─▶ Fusion ─▶ Category Confidence
    ├─▶ Vision Embedding (MobileNetV3-Small) ────┘           Severity Score
    │                                                         Priority Score
    ├─▶ Duplicate Detection (cosine similarity)               ↓
    │                                                 Human Verification
    └─▶ Issue Linkage (cluster matching)                       ↓
                                                    Verified / Corrected / Rejected
```

---

## ⚡ Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 20+ |
| Docker | 24+ (for PostgreSQL) |
| Android Studio | Ladybug (2024.2) |
| JDK | 21 |

### 1. Clone and configure

```bash
git clone https://github.com/helloabhishek2004/Civicsense.git
cd Civicsense

# Copy and edit root environment variables
cp .env.example .env
# Required: set DATABASE_URL, VITE_GOOGLE_MAPS_API_KEY, etc.
```

### 2. Start the database

```bash
docker compose up -d
```

### 3. Start the backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 4. Start the web dashboard

```bash
cd dashboard
npm install
cp .env.example .env   # or create dashboard/.env
npm run dev
# Dashboard at http://localhost:5173
```

### 5. Build the Android app

```bash
cd android
cp local.properties.example local.properties
# Edit local.properties: set MAPS_API_KEY and API_BASE_URL
./gradlew assembleDebug
# APK at android/app/build/outputs/apk/debug/app-debug.apk
```

Or open the `android/` folder in Android Studio and run directly on device/emulator.

> **One-command local demo (Windows):** Run `start_demo.bat` from the repo root. See [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md) for the full walkthrough.

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| Android App | Kotlin 2.0, Jetpack Compose (BOM 2024.10), Material 3 1.3, Google Maps Compose 6.2 |
| Mobile Scaffold | React Native / Expo SDK 52 + TypeScript |
| Web Dashboard | React 18.3, TypeScript 5.6, Vite 5.4, Tailwind CSS 3.4, TanStack Query v5, Recharts, Leaflet |
| Backend | Python 3.11, FastAPI 0.115, Pydantic v2, SQLAlchemy 2.0, Alembic, psycopg3 |
| Database | PostgreSQL 16 |
| AI — Text | MiniLM L6 v2 (sentence-transformers, 384-dim) |
| AI — Vision | MobileNetV3-Small fine-tuned (PyTorch/torchvision, 576-dim) |
| Infrastructure | Docker Compose |
| Testing | pytest + Vitest + Android Instrumented Tests |

---

## 📁 Repository Structure

```
Civicsense/
├── android/              # Native Android app (Kotlin + Compose)
├── backend/              # FastAPI Python backend + Alembic migrations
├── dashboard/            # React + Vite web authority dashboard
├── mobile/               # React Native / Expo scaffold
├── ml/                   # ML training, evaluation, and inference scripts
├── models/               # Downloaded model weights (gitignored — see below)
├── datasets/             # Benchmark datasets and evaluation run results
├── shared/               # Canonical JSON schemas shared across clients
├── docs/                 # Architecture, API reference, deployment guide
├── scripts/              # Developer utilities (demo, ADB, LAN setup)
├── presentation/         # HTML project presentation
├── artifacts/            # ML experiment artifacts and reports
├── docker-compose.yml    # PostgreSQL 16 local database
├── Makefile              # Common developer commands
├── .env.example          # Environment variable template
└── CONTRIBUTING.md       # Contribution guide
```

> **`models/` directory** is gitignored. Model weights are downloaded automatically by `backend/app/services/` on first run, or can be seeded via `ml/scripts/download_models.py`. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## 🤖 AI / ML Design Principles

CivicSense is explicit about the nature and limitations of its AI pipeline:

- **Confidence ≠ Severity ≠ Priority.** These are three independent fields, each computed by separate heuristics, and all displayed separately to human reviewers.
- **No auto-apply.** AI classifications are always subject to human verification (`VERIFIED` / `CORRECTED` / `REJECTED`) before influencing any operational decision.
- **Explicit uncertainty.** The system supports `UNKNOWN`, `OTHER`, `REVIEW_REQUIRED`, `LOW_CONFIDENCE`, and `CONFLICTING_EVIDENCE` states — never forcing an input into a false category.
- **Baselines first.** Text and vision unimodal baselines were benchmarked independently before fusion was introduced. Evaluation reports are in `datasets/evaluation_runs/`.
- **Raw evidence is never discarded.** Original photos are durably stored; embeddings are derived views, not replacements.

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design, component boundaries, data flow |
| [`docs/API.md`](docs/API.md) | REST API reference for `/api/v1/` endpoints |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Full deployment and environment setup guide |
| [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md) | Step-by-step demo instructions |
| [`docs/AI_EVALUATION.md`](docs/AI_EVALUATION.md) | ML evaluation methodology and results |
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | Research design and dataset curation approach |

---

## 🧪 Testing

```bash
# Backend
cd backend && pytest

# Dashboard
cd dashboard && npm test

# Android unit tests
cd android && ./gradlew testDebugUnitTest

# Dashboard type check
cd dashboard && npx tsc --noEmit

# Backend lint + type check
cd backend && ruff check . && mypy .
```

Current test coverage:
- **Android**: 74 unit tests — 100% pass
- **Dashboard**: 85 unit tests — 100% pass
- **Backend**: pytest suite covering API endpoints, services, and ML pipeline contracts

---

## 🤝 Contributing

CivicSense welcomes contributions — bug reports, feature ideas, documentation improvements, and ML dataset contributions.

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a PR. All contributors are expected to follow the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

**Found a security vulnerability?** Please read [`SECURITY.md`](SECURITY.md) and report privately — do not open a public issue.

---

## 📜 License

CivicSense is released under the [MIT License](LICENSE).

Copyright © 2026 CivicSense Team

---

<div align="center">
Built with ❤️ for civic technology
</div>
