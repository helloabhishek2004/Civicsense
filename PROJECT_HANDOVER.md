# CivicSense — Project Handover & Developer Blueprint

> **To the Incoming AI Coding Agent / Senior Engineer:**
>
> Welcome to **CivicSense**. This document is your primary briefing, architectural blueprint, and operational playbook. It reflects the current state of the codebase as of September 2026—what is working, what is staged, what is missing, and how to execute the remaining roadmap.
>
> **Read this entire document before generating or modifying code.**

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Operational Governance](#2-operational-governance)
3. [Architecture Overview](#3-architecture-overview)
4. [Implementation History](#4-implementation-history)
5. [Current System Status](#5-current-system-status)
6. [Repository Directory Guide](#6-repository-directory-guide)
7. [Subsystem Deep Dives](#7-subsystem-deep-dives)
8. [Frontend Dashboard Architecture](#8-frontend-dashboard-architecture)
9. [Frontend Audit Findings](#9-frontend-audit-findings)
10. [API Reference](#10-api-reference)
11. [Recommended Next Steps](#11-recommended-next-steps)
12. [Critical Traps & Anti-Patterns](#12-critical-traps--anti-patterns)
13. [Developer Command Cheat Sheet](#13-developer-command-cheat-sheet)

---

## 1. Executive Summary

### 1.1 What CivicSense Is
**CivicSense** is an enterprise-grade civic issue reporting, intelligence, and resolution platform. It bridges raw citizen complaints submitted via mobile devices with structured, prioritized municipal engineering workflows.

### 1.2 The Core Architectural Axiom: `Report != Issue`
CivicSense separates:
- **`Report`**: An individual citizen submission event (photos, raw text, GPS, device metadata, citizen profile).
- **`Issue`**: A deduplicated, real-world physical defect on the ground. Multiple `Report` instances cluster into a single canonical `Issue`.

```
Citizen A Report ──┐
Citizen B Report ──┼──► [Similarity Engine] ──► Canonical Issue ──► [Priority Engine] ──► Municipal Work Order
Citizen C Report ──┘
```

### 1.3 System Completion Status: ~65%
- **Intake, Edge Preprocessing & Upload**: **~85%** (Android app production-ready, 76 tests)
- **Backend API & Department Operations**: **~85%** (426 tests, 10 migrations, 29 endpoints)
- **Similarity & Deduplication Engine**: **100%** (Sprint 3 complete, 67+21 tests)
- **Dynamic Priority Ranking Engine**: **100%** (Sprint 4 complete, 53 tests)
- **AI/ML Model Research & Staged Offline**: **~65%** (models trained, not wired to live API)
- **Live AI Server Integration**: **~15%** (still runs demo heuristics)
- **Authority Dashboard**: **~70%** (report-centric, no issue UI yet)

---

## 2. Operational Governance

Every incoming agent must adhere to [AGENTS.md](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/AGENTS.md). Core rules:

- **`AGENTS.md`**: Operational playbook and governance constitution (HOW to act).
- **`memory.md`**: Durable factual record of implementation state (WHAT exists).
- **Frozen Benchmark**: `datasets/benchmark_v1/benchmark_dataset.jsonl` (SHA-256: `e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b`). Never modify.
- **Do Not Assume**: Verify code ground truth. The running repository is the sole authority.
- **Modular Monolith**: No premature microservices, Kafka, Celery, or Redis.
- **Pre-Completion Verification**: Run all tests before marking complete.

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CITIZEN LAYER                                │
│  Android App (Kotlin/Compose)  │  Expo App (React Native)          │
│  Edge preprocessing, upload    │  Scaffold only                    │
└──────────────┬──────────────────────────────────────────────────────┘
               │ POST /api/v1/reports
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Reports  │  │  Issues  │  │ Matches  │  │   Departments    │   │
│  │ Service  │  │ Service  │  │ Service  │  │    Service       │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │              │                  │             │
│  ┌────▼──────────────▼──────────────▼──────────────────▼─────────┐  │
│  │                    Data Access Layer                           │  │
│  │              SQLAlchemy 2.0 + Alembic Migrations              │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼────────────────────────────────────┐  │
│  │                    PostgreSQL 16                               │  │
│  │  reports, issues, report_issue_matches, evidences,           │  │
│  │  ai_analyses, verifications, departments, report_assignments  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────────────────┘
               │ GET /api/v1/reports, /issues, /matches
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  AUTHORITY DASHBOARD (React 18)                      │
│  Reports Queue │ Report Detail │ Departments │ Map │ AI Operations  │
│  (100% report-centric — Issue UI pending)                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation History

### Phase 1: Foundation & Mobile
- Android Kotlin/Compose app with edge preprocessing, camera, upload, polling
- FastAPI backend with 11-state lifecycle, idempotent ingestion, evidence storage
- Municipal department operations (6 seeded divisions, assignment/rejection workflow)
- React 18 + Vite dashboard with reports, departments, map, analytics

### Phase 2: AI Pipeline Hardening
- Image ingestion gate (MIME, size, dimensions, decompression bomb defense)
- Text sanitization (NFKC normalization, control char stripping)
- Standardized `NormalizedPrediction` schema

### Phase 3.2-3.5: ML Research & Evaluation
- 300-sample frozen benchmark (6 classes, 50 samples each)
- MobileNetV3-Small vision backbone (43.33% accuracy, 90% pothole recall)
- MiniLM-L6-v2 text classifier (87.33% accuracy, 88% ensemble)
- Multimodal fusion engine (79.67% accuracy, 100% selective auto-triage on 27%)

### Phase 4A: Semantic Text Intelligence
- MiniLM + Logistic Regression head, McNemar p=0.0001 significant lift
- Superior calibration (ECE 0.0578 vs 0.1561 deterministic)

### Phase 3 (Sprint 3): Similarity & Deduplication Engine ✅
- Haversine distance + cosine text similarity + category match
- 3-tier routing: AUTO_LINK / CANDIDATE / NEW_ISSUE
- `report_issue_matches` audit trail table (migration `0009`)
- Match review API (approve/reject/supersede)
- 67 similarity tests + 21 review API tests

### Phase 4 (Sprint 4): Dynamic Priority Ranking Engine ✅
- 5-factor weighted formula: severity, volume, unique reporters, recency, persistence
- Configurable thresholds: CRITICAL >= 65, HIGH >= 40, MEDIUM >= 15
- Auto-recomputation on report linkage and match approval
- Batch recompute endpoint (admin-only)
- 53 priority tests

### Dashboard Architecture Audit ✅
- Complete audit of frontend/backend integration
- Identified gap: 100% report-centric, zero Issue concept in frontend
- Recommended approach: Upgrade existing Reports page (not build separate Issues page)

---

## 5. Current System Status

### 5.1 Test Counts
| Component | Tests | Status |
|---|---|---|
| Backend (pytest) | 426 | All passing |
| Dashboard (vitest) | 59 | All passing |
| Android (gradle) | 76 | All passing |
| **Total** | **561** | **All passing** |

### 5.2 Backend Endpoints (29 total)
| Group | Endpoints | Key Routes |
|---|---|---|
| Health | 1 | `GET /api/v1/health` |
| Reports | 14 | CRUD, transition, verify, assign, acknowledge, complete, reject, AI |
| Issues | 4 | List (priority-sorted), detail, priority breakdown, batch recompute |
| Match Review | 3 | Pending list, approve, reject |
| Departments | 4 | List, detail, stats, department reports |
| AI Operations | 3 | Jobs, metrics, health |

### 5.3 Database Migrations (10 total)
`0001`-`0007`: Core schema, AI jobs, edge metadata, citizen info, departments
`0008`: Text embeddings (reports + issues)
`0009`: Report-issue match audit trail
`0010`: Issue priority fields (score, level, computed_at, breakdown)

### 5.4 What's Implemented vs Missing

| Capability | Status |
|---|---|
| Citizen report submission | ✅ Fully working |
| Backend report ingestion | ✅ Fully working |
| 11-state lifecycle management | ✅ Fully working |
| Department assignment/rejection | ✅ Fully working |
| Similarity & deduplication engine | ✅ Fully working |
| Dynamic priority ranking | ✅ Fully working |
| Match review workflow (API) | ✅ Fully working |
| AI vision/text models | ⚠️ Trained, not wired to live API |
| Dashboard report views | ✅ Fully working |
| Dashboard issue views | ❌ Missing |
| Dashboard match review UI | ❌ Missing |
| Dashboard priority breakdown UI | ❌ Missing |

---

## 6. Repository Directory Guide

```
CivicSense/
├── AGENTS.md                    # Operational constitution
├── memory.md                    # Current implementation state
├── PROJECT_HANDOVER.md          # This document
├── docker-compose.yml           # PostgreSQL 16
├── pyproject.toml               # Python dependencies
│
├── android/                     # Native Android app (Kotlin/Compose)
│   └── app/src/main/java/com/civicsense/
│       ├── core/edge/           # Edge preprocessing
│       ├── core/network/        # Upload client
│       └── ui/screens/          # Home, MyReports, ReportWizard
│
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── api/v1/routes/       # 29 REST endpoints
│   │   ├── models/              # SQLAlchemy 2.0 ORM (Report, Issue, etc.)
│   │   ├── schemas/             # Pydantic v2 validation
│   │   ├── services/
│   │   │   ├── reports/         # Report orchestration
│   │   │   ├── similarity/      # Similarity & dedup engine
│   │   │   ├── priority/        # Priority ranking engine
│   │   │   ├── departments/     # Department operations
│   │   │   └── ai/              # AI/ML adapters (staged offline)
│   │   └── evaluation/          # Headless evaluation suite
│   ├── alembic/versions/        # 10 migrations (0001-0010)
│   └── tests/                   # 426 tests
│
├── dashboard/                   # React 18 + Vite + TypeScript
│   ├── src/
│   │   ├── features/            # Reports, Departments, Map, AI Ops
│   │   ├── core/components/     # 13 reusable UI components
│   │   ├── services/            # API client, repository pattern
│   │   └── types/               # TypeScript types
│   └── package.json
│
├── mobile/                      # React Native Expo scaffold
├── datasets/                    # Benchmark, training splits
├── models/                      # Trained model weights
├── artifacts/                   # Evaluation bundles
└── scripts/                     # Training, curation, evaluation
```

---

## 7. Subsystem Deep Dives

### 7.1 Similarity & Deduplication Engine
**Location**: `backend/app/services/similarity/`

**How it works**:
1. On report submission, `ReportService.submit_report()` calls `process_similarity_match()`
2. Engine queries open issues within 50m radius (Haversine distance)
3. Computes cosine similarity between MiniLM text embeddings
4. Checks category match
5. Routes to: AUTO_LINK (score >= 0.70), CANDIDATE (0.45-0.70), or NEW_ISSUE (< 0.45)
6. Creates `ReportIssueMatch` audit record with component scores

**Config** (in `core/config.py`):
- `SIMILARITY_TEXT_WEIGHT = 0.40`
- `SIMILARITY_DISTANCE_WEIGHT = 0.35`
- `SIMILARITY_CATEGORY_WEIGHT = 0.25`
- `SIMILARITY_RADIUS_METERS = 50`
- `SIMILARITY_HIGH_THRESHOLD = 0.70`
- `SIMILARITY_MEDIUM_THRESHOLD = 0.45`

### 7.2 Dynamic Priority Ranking Engine
**Location**: `backend/app/services/priority/`

**Formula**:
```
score = 0.30*severity + 0.25*volume + 0.20*reporters + 0.15*recency + 0.10*persistence
```

**Components**:
- `severity_score`: Max severity across linked reports (CRITICAL=1.0, HIGH=0.75, MEDIUM=0.5, LOW=0.25)
- `report_volume_score`: Log-scaled count with saturation at 50 reports
- `unique_reporter_score`: Count of distinct citizen_ids, normalized
- `recency_score`: Exponential decay from most recent report (half-life 7 days)
- `persistence_score`: How long issue has been active (max 90 days)

**Auto-recomputation triggers**:
- After AUTO_LINK in similarity engine
- After NEW_ISSUE creation
- After match approval in review service

### 7.3 Match Review Workflow
**Location**: `backend/app/services/similarity/review.py`

**Flow**:
1. Officer calls `GET /api/v1/matches/pending` to see CANDIDATE matches
2. Reviews match details (component scores, reasoning)
3. Approves via `POST /api/v1/matches/:id/approve` (links report to issue)
4. Or rejects via `POST /api/v1/matches/:id/reject` (keeps report unlinked)

**Auth**: All match review endpoints require `X-Reviewer-ID` header.

---

## 8. Frontend Dashboard Architecture

### 8.1 Framework & Tooling
| Aspect | Technology |
|---|---|
| Framework | React 18.3.1 + TypeScript 5.6.3 (strict) |
| Build | Vite 5.4.11 |
| State | TanStack React Query 5.62.7 |
| Routing | React Router DOM 6.28.0 |
| Styling | Tailwind CSS 3.4.16 (no component library) |
| Animation | motion 13.2.0 |
| Map | Google Maps (primary) + Leaflet (fallback) |
| Icons | lucide-react |
| Testing | Vitest 2.1.8 + Testing Library |

### 8.2 Route Structure
| Route | Component | Purpose |
|---|---|---|
| `/` | OverviewPage | KPIs, urgent triage queue |
| `/reports` | ReportsPage | Report list DataTable |
| `/reports/:id` | ReportDetailPage | Full report detail + actions |
| `/ai-operations` | AIOperationsPage | AI pipeline monitoring |
| `/map` | MapPage | Geospatial incident view |
| `/analytics` | AnalyticsPage | Charts and metrics |
| `/departments` | DepartmentsPage | Department directory |
| `/departments/:id` | DepartmentDetailPage | Department work queue |

### 8.3 API Client Architecture
- Custom `ApiClient` class (native `fetch()`)
- Repository pattern: `IReportRepository` -> `ApiReportRepository` / `MockReportRepository`
- Base URL: `http://localhost:8000/api/v1`
- `VITE_DATA_MODE` env var: `mock` or `api`

### 8.4 Reusable Components
`DataTable`, `FilterBar`, `StatusBadge`, `SeverityBadge`, `PriorityBadge`, `CivicButton`, `Modal`, `Drawer`, `StatCard`, `ErrorBanner`, `EmptyState`, `LoadingSkeleton`, `PageHeader`

---

## 9. Frontend Audit Findings

### 9.1 Current Product Model: 100% Report-Centric

| Question | Answer |
|---|---|
| Is the UI report-centric or issue-centric? | **Report-centric.** No Issue concept in frontend. |
| Can an officer see all reports belonging to one Issue? | **No.** No endpoint, no UI. |
| Can an officer see why an Issue has its current priority? | **No.** Priority breakdown endpoint exists but no UI. |
| Can an officer navigate from a report to its Issue? | **No.** `issue_id` dropped during mapping. |
| Can an officer navigate from an Issue to its reports? | **No.** No Issue detail page. |
| Can an officer review pending duplicate candidates? | **No.** Match review API exists but no UI. |
| Can an officer act on an Issue directly? | **No.** All actions are report-level. |

### 9.2 Critical Gaps

**Backend Limitations**:
1. No `GET /api/v1/issues/:id/reports` endpoint
2. No `issue_id` filter on `GET /api/v1/reports`
3. `IssueUpdate` schema defined but no PATCH endpoint

**Frontend Limitations**:
1. `ReportItem` type missing `issueId`
2. `mapBackendToReportItem` drops `issue_id`
3. No issue endpoints in `endpoints.ts`
4. No issue types in `types/`
5. No issue repository
6. No Issue detail page
7. No match review UI
8. No priority breakdown display

### 9.3 Redundancy to Avoid
- Do NOT build a separate Issues queue that duplicates Reports page columns
- Do NOT create new design system components (reuse existing `core/components/`)
- Do NOT duplicate filter/table infrastructure

---

## 10. API Reference

### 10.1 Report Endpoints
| Method | Path | Response | Notes |
|---|---|---|---|
| `POST` | `/api/v1/reports` | `ReportRead` | 201 Created; idempotent via `X-Idempotency-Key` |
| `GET` | `/api/v1/reports` | `ReportListResponse` | Paginated, filterable by citizen_id, department, status, category, priority |
| `GET` | `/api/v1/reports/stats` | `ReportStats` | Aggregated metrics |
| `GET` | `/api/v1/reports/:id` | `ReportRead` | By UUID or tracking ID |
| `PATCH` | `/api/v1/reports/:id/transition` | `ReportRead` | Lifecycle state machine |
| `POST` | `/api/v1/reports/:id/verify` | `ReportRead` | Human verification verdict |
| `POST` | `/api/v1/reports/:id/assign` | `ReportRead` | Department assignment |
| `POST` | `/api/v1/reports/:id/acknowledge` | `ReportRead` | Department accepts |
| `POST` | `/api/v1/reports/:id/complete` | `ReportRead` | Department resolves |
| `POST` | `/api/v1/reports/:id/department-reject` | `ReportRead` | Department declines |
| `GET` | `/api/v1/reports/:id/assignments` | `list[AssignmentRead]` | Assignment audit history |
| `POST` | `/api/v1/reports/:id/ai/process` | `AIJobRead` | Queue AI processing |
| `GET` | `/api/v1/reports/:id/ai` | `ReportAIResult` | Latest AI assessment |
| `GET` | `/api/v1/reports/:id/ai/events` | `list[AIJobEventRead]` | AI stage audit events |

### 10.2 Issue Endpoints
| Method | Path | Response | Notes |
|---|---|---|---|
| `GET` | `/api/v1/issues` | `IssueListResponse` | Sorted by priority (default), created, updated, reports |
| `GET` | `/api/v1/issues/:id` | `IssueRead` | Single issue detail |
| `GET` | `/api/v1/issues/:id/priority` | `PriorityBreakdownRead` | Full component breakdown |
| `POST` | `/api/v1/issues/recompute-priority` | `dict` | Admin-only batch recompute |

### 10.3 Match Review Endpoints
| Method | Path | Response | Notes |
|---|---|---|---|
| `GET` | `/api/v1/matches/pending` | `MatchListResponse` | Requires `X-Reviewer-ID` |
| `POST` | `/api/v1/matches/:id/approve` | `ReviewActionResponse` | Requires `X-Reviewer-ID` |
| `POST` | `/api/v1/matches/:id/reject` | `ReviewActionResponse` | Requires `X-Reviewer-ID` |

### 10.4 Key Response Shapes

**`ReportRead`**: `id`, `tracking_id`, `status`, `category`, `citizen_*`, `latitude`, `longitude`, `description`, `issue_id` (nullable UUID), `department`, `priority`, `evidences[]`, `ai_analyses[]`, `verifications[]`, `assignments[]`, `created_at`, `updated_at`

**`IssueRead`**: `id`, `title`, `category`, `status`, `primary_latitude`, `primary_longitude`, `report_count`, `priority_score`, `priority_level`, `priority_computed_at`, `created_at`, `updated_at`

**`PriorityBreakdownRead`**: `issue_id`, `priority_score`, `priority_level`, `priority_computed_at`, `breakdown` (dict with `severity_score`, `report_volume_score`, `unique_reporter_score`, `recency_score`, `persistence_score`, `weighted_sum`, `final_score_0_100`, `formula_version`)

**`MatchRead`**: `id`, `report_id`, `issue_id`, `action`, `status`, `combined_score`, `text_similarity`, `distance_meters`, `category_match`, `reasoning[]`, `created_at`

---

## 11. Recommended Next Steps

### 11.1 Immediate: Backend Gaps (30 min)
1. Add `GET /api/v1/issues/:id/reports` endpoint
2. Add `issue_id` filter to `GET /api/v1/reports`
3. Write tests

### 11.2 Frontend Data Layer (1 hour)
1. Add `issueId` to `ReportItem` type
2. Add Issue/match types to `types/`
3. Add issue/match endpoints to `endpoints.ts`
4. Fix `mapBackendToReportItem` to include `issueId`
5. Add issue repository methods

### 11.3 Issue Detail Page (2 hours)
1. Create `IssueDetailPage` with priority breakdown, linked reports
2. Add `/issues/:id` route
3. Add Issues nav item to Sidebar

### 11.4 Reports Page Integration (1.5 hours)
1. Add "Issue" column to Reports DataTable
2. Add issue badge/grouping indicator
3. Add "View Issue" link from ReportDetailPage

### 11.5 Match Review UI (1.5 hours)
1. Create `PendingMatchesPanel` component
2. Add to IssueDetailPage or as standalone modal
3. Wire approve/reject actions

**Total estimated effort**: 6-7 hours for full issue-centricity.

---

## 12. Critical Traps & Anti-Patterns

1. **Do not touch the frozen benchmark** (`datasets/benchmark_v1/`).
2. **Do not confuse Python `tracemalloc` with true process RSS** (use `psutil`).
3. **Do not add premature microservices** (CivicSense is a modular monolith).
4. **Do not break UTC timestamp serialization** (always `Z` suffix).
5. **Do not auto-close tickets on department rejection** (return to `PRIORITIZED`).
6. **Do not drop `issue_id` in frontend mapping** (the critical gap identified in audit).
7. **Do not build a separate Issues page** (upgrade existing Reports page instead).

---

## 13. Developer Command Cheat Sheet

### Backend
```bash
# Run all 426 tests
pytest backend/tests -q

# Lint
ruff check backend

# Typecheck
mypy backend/app

# Start dev server
uvicorn backend.app.main:app --reload --port 8000

# Run migrations
alembic upgrade head
```

### Dashboard
```bash
cd dashboard
npm run test        # 59 tests
npm run typecheck   # TypeScript
npm run build       # Production
npm run dev         # Dev server (localhost:5173)
```

### Android
```bash
cd android
./gradlew testDebugUnitTest    # 76 tests
./gradlew assembleDebug        # APK
```

### Benchmark Integrity
```bash
python -c "import hashlib; h=hashlib.sha256(open('datasets/benchmark_v1/benchmark_dataset.jsonl','rb').read()).hexdigest(); assert h=='e988474dd46cee4c3b17010fb32af1a50ff750ea32579d8e8ab7ef8b0fd2e60b', f'HASH MISMATCH: {h}'; print('BENCHMARK VERIFIED')"
```

---

## Conclusion

CivicSense has a battle-tested backend with 426 passing tests, a fully functional similarity engine, and a dynamic priority ranking system. The frontend is polished but entirely report-centric. The smallest next feature that makes CivicSense genuinely issue-centric is: **add `issueId` to the frontend ReportItem, display it in the Reports DataTable, and create an IssueDetailPage with priority breakdown and linked reports.** This is approximately 6-7 hours of work across 10-12 files, requiring zero new design components.

Build cleanly, maintain separation of concerns, verify every step, and respect the governance rules. Good luck!
