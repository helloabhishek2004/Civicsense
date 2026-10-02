# Changelog

All notable changes to CivicSense are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

---

## [0.1.0] — 2026-10-02

First public open-source release. Pre-production research prototype demonstrating the full civic issue reporting and AI-assisted triage pipeline.

### Added

#### Android App (Kotlin + Jetpack Compose)
- Full 4-step report wizard: evidence capture → description + category → live map location → review & submit
- Real camera capture (FileProvider, EXIF stripping) and gallery picker
- Material 3 pull-to-refresh on Home and My Reports screens
- Real-time report status polling (6 s per-report, 10 s list polling, lifecycle-aware)
- 6-stage resolution timeline with department display and reassignment state
- Offline report queueing with `QUEUED_OFFLINE` state semantics
- Material 3 Expressive loading indicator (5-shape cubic Bézier morphing)
- Deterministic 4-state onboarding engine with profile validation
- Dynamic theme system (System / Light / Dark) persisted in DataStore
- Adaptive icon, themed monochrome icon (Android 13+)
- High-refresh-rate display mode support
- Citizen identity fields (`citizen_name`, `citizen_phone`, `citizen_email`, `citizen_postal_code`) transmitted with reports
- Device-scoped `citizen_id` (UUIDv4) for report ownership
- Google Maps Compose map picker with center-pin location selection
- 74 unit tests — 100% pass rate

#### Web Authority Dashboard (React + Vite + TypeScript)
- Report queue with sortable, filterable table
- Interactive Leaflet map with issue cluster overlay
- Analytics panel: category distribution, trend lines, resolution rates
- AI operations view: confidence scores, embedding explorer
- Department management and assignment workflow
- Aceternity hover-expand sidebar with spring animation
- Full mock-data mode (`VITE_DATA_MODE=mock`) for UI development without backend
- 85 unit tests — 100% pass rate
- Vite build and TypeScript strict compilation verified

#### FastAPI Backend
- Versioned REST API at `/api/v1/`
- Pydantic v2 request/response schemas with strict validation
- 11 Alembic migrations covering full schema lifecycle
- `Report` / `Issue` domain separation (never conflated)
- Multimodal AI pipeline: MiniLM L6 v2 text embeddings + MobileNetV3-Small visual embeddings
- Weighted fusion baseline evaluated against unimodal baselines
- Cosine-similarity duplicate detection and issue clustering
- Confidence, severity, and priority as independent fields
- Human verification layer (`VERIFIED` / `CORRECTED` / `REJECTED`)
- Explicit uncertainty states (`UNKNOWN`, `OTHER`, `REVIEW_REQUIRED`, `LOW_CONFIDENCE`, `CONFLICTING_EVIDENCE`)
- PostgreSQL 16 via SQLAlchemy 2.0 async ORM (psycopg3)
- LAN CORS auto-permit for cross-device demo (`10.*`, `192.168.*`, `172.16-31.*`)

#### ML / AI Pipeline
- MiniLM L6 v2 text embedding pipeline (384-dim sentence vectors)
- MobileNetV3-Small vision model fine-tuned on 6 civic categories (576-dim)
- Benchmark dataset `v1` with curated, annotated civic images
- Evaluation runs: baseline text-only, vision-only, fusion, forensics, MobileNetV3 pilot
- Calibration reports, confusion matrices, latency profiles, statistical tests
- AI experiment artifacts in `artifacts/` with manifest and selection reports

#### React Native / Expo Scaffold
- Typed API client with `AbortController` timeout and `X-Request-ID`
- `ReportCreateScreen` and `ReportDetailScreen` with state-driven navigation
- Civic Path adaptive icon assets

#### Infrastructure & Developer Experience
- Docker Compose (PostgreSQL 16) one-command database setup
- `Makefile` with common dev commands
- `start_demo.bat` one-click local demo launcher (Windows)
- `scripts/get_lan_ip.ps1` — automatic LAN IP detection for cross-device demo
- `scripts/set_phone_server_url.py` — portable ADB URL injection
- `scripts/sync_apk_lan_ip.py` — APK distribution utility
- `.env.example` with all required and optional variables documented
- Debug APK: `CivicSense-Android-v0.1.0-debug.apk`

#### Documentation
- `docs/ARCHITECTURE.md` — system design and data flow
- `docs/API.md` — REST API reference
- `docs/DEPLOYMENT.md` — full deployment guide
- `docs/DEMO_RUNBOOK.md` — step-by-step demo instructions
- `docs/AI_EVALUATION.md` — ML evaluation methodology and results
- `docs/METHODOLOGY.md` — research design and dataset curation
- `docs/RESULTS_AND_LIMITATIONS.md` — honest assessment of prototype limitations
- `README.md` — professional open-source README with architecture overview
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- `THIRD_PARTY_NOTICES.md` — attribution for all open-source dependencies
- GitHub issue templates (Bug, Feature, ML/Dataset) and PR template
- GitHub Actions CI workflow (backend, dashboard, Android, secret scan)

### Security

- Removed hardcoded Google Maps API key from committed source (`dashboard/src/core/config/env.ts`)
- Replaced real key with placeholder in `android/local.properties.example`
- Removed internal AI agent development files from git tracking (`memory.md`, `skills-lock.json`, planning documents)
- Added CI secret scan job to reject commits containing API key patterns

### Notes

- This is a **pre-production research prototype**. Not intended for production deployment without significant hardening (authentication, access control, evidence storage, privacy compliance).
- The Android app uses a prototype `citizen_id` UUID — not real authentication.
- The web dashboard has no login/auth in this version.
- Model weights in `models/` are gitignored; they are downloaded at runtime by the backend service layer.

[0.1.0]: https://github.com/helloabhishek2004/Civicsense/releases/tag/v0.1.0
