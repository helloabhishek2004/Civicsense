# CivicSense — Implementation Memory

## 1. Project Architecture

The current high-level system architecture is a monorepo consisting of:

- **Citizen Mobile Application**: Native Android (Kotlin + Jetpack Compose) and React Native + Expo (TypeScript strict mode).
- **Backend API**: Python FastAPI service providing versioned REST endpoints (`/api/v1/`).
- **Relational Database**: PostgreSQL 16 managed via SQLAlchemy 2.0 ORM and Alembic migrations.
- **Shared Contracts**: Canonical JSON Schemas governing client-to-server payloads.
- **Service Interfaces**: Abstract interfaces for future vision, text, fusion, similarity, decision, and analytics modules (raising `NotImplementedError`; no fake AI).
- **Developer Orchestration**: Docker Compose for local database infrastructure, accompanied by PowerShell (`scripts/dev.ps1`), Bash (`scripts/dev.sh`), and `Makefile` task runners.

---

## 2. Applications

### Citizen Mobile Application (Native Android — Phase 1.3 UX Refinement, Report Flow Redesign & Refresh Interaction)

**Status:** Implemented (Phase 1.3 UX Refinement, Report Flow Redesign & Refresh Interaction)

- **Platform & Toolchain**: Kotlin 2.0.21, Jetpack Compose (BOM 2024.10.01), Material 3 (1.3.1), Android Gradle Plugin 8.7.2, targetSdk 35, compileSdk 35, minSdk 26, OpenJDK 21. Google Maps Compose 6.2.1 and Google Play Services Maps 19.0.0.
- **Directory**: `android/` with package namespace `com.civicsense`.
- **Navigation Shell & Back Handling**: 4 destinations via Material 3 `NavigationBar` (`Home`, `My Reports`, `Report`, `Profile`) + nested Navigation Compose stack. Root tabs back press returns to `Home` first before exiting. Sub-screens pop back stack cleanly; report wizard navigates step-by-step.
- **Entry & Onboarding**: Android SplashScreen API integration, 3-slide `HorizontalPager` onboarding with page indicators, and local profile setup.
- **Profile Setup & Input Placeholders**: Simplified phone placeholder to strictly `9874563210` with persistent label and helper text (`10-digit Indian mobile number`). Realistic input placeholders across all screens: name (`Abhishek S`), locality (`Near the public library, Main Road`), PIN (`695xxx`), description (`Describe what happened...`). Strict Indian mobile normalization (strips `+91` or 12-digit `91`, requires 10 digits starting with 6, 7, 8, or 9; no naive `takeLast(10)`), 6-digit postal PIN validation, and a brief 700ms completion screen before entering the dashboard.
- **Theming & Appearance**: System-wide theme engine supporting `SYSTEM`, `LIGHT`, and `DARK` modes persisted in DataStore (`PreferenceRepository`) with an in-app Appearance selector dialog in Profile and dynamic updates in `MainActivity`.
- **Display & High Refresh Rate**: Dynamic display mode inspection querying `display.supportedModes`, filtering modes matching physical resolution, selecting the highest refresh rate mode (>60Hz), configuring `window.attributes.preferredDisplayModeId` and `preferredRefreshRate`, and emitting diagnostic logs in debug builds under tag `CivicSenseDisplay`. Respects OS/battery/thermal constraints without forcing.
- **Report Entry Redesign & FAB**: Replaced initial dual report buttons with a thumb-friendly bottom-right Floating Action Button (`+` icon, 64dp, `CivicGreen`) navigating directly to the evidence capture screen with camera and gallery picker.
- **Persistent 4-Stage Report Progress Indicator**: `CivicReportProgressBar` providing an animated, 4-stage segmented indicator (Step 1: Evidence, Step 2: Details, Step 3: Location, Step 4: Review). Derived directly from wizard state, smoothly animating between steps, and kept visible at 100% on Review even during submission.
- **Real Submission State & Idempotency**: Explicit `SubmissionState` (`IDLE`, `SUBMITTING`, `SUCCESS`, `ERROR`) with double-tap suppression. Shows Material 3 Expressive `CivicContainedLoadingIndicator` card during submission processing. Real immediate repository persistence without artificial delays. On error, preserves entire draft state with retry button on `ReviewScreen`.
- **Material 3 Pull-to-Refresh & Expressive Loading**:
  - *Official Material 3 Pull-to-Refresh* (`PullToRefreshBox` & `PullToRefreshDefaults.Indicator`): Integrated the official Material 3 1.3.1 `PullToRefreshBox` and `rememberPullToRefreshState()` across both `HomeScreen` and `MyReportsScreen`. Provides authentic Google apps / Chrome / Gmail pull physics: circular arrow arc dynamically scaling with drag distance, automatic snap to indeterminate spinning indicator at threshold release, and smooth automatic upward exit on completion. Lifecycle is strictly managed in `try / catch / finally` with atomic concurrency protection, preventing duplicate refreshes or stuck states.
  - *M3 Expressive Loading Indicator* (`CivicLoadingIndicator` / `CivicContainedLoadingIndicator`): 72-point cubic Bézier parametric continuous shape morphing across 5 M3 Expressive geometric shapes (circle, 4-petal clover/flower, squircle, 4-point star/diamond, rounded pill/capsule) with breathing scale pulse (0.94x–1.06x) and smooth continuous rotation. Dedicated to high-emphasis wait states such as report submission on `ReviewScreen`.
  - *Data Source Decoupling & Typed Refresh State*: `ReportRepository` defines `ReportsDataSource` interface and `LocalReportsDataSource` default implementation, decoupling local mock storage from future REST API endpoints (`/api/v1/reports`). Exposes typed `RefreshResult` (`Success`, `NoData`, `Error`). On refresh failure, preserves existing in-memory reports without data loss and surfaces errors via Material 3 `SnackbarHost`.
  - *Empty State Refreshability*: Empty report views (`MyReportsScreen`) wrap contents in `Modifier.verticalScroll(rememberScrollState())`, guaranteeing that citizens can pull to refresh even when 0 reports exist. Preserves active filter selection (`ALL`, `ACTIVE`, `RESOLVED`).
- **Honest Citizen Reporting Wizard**:
  - *Evidence Capture*: Real camera capture (`ActivityResultContracts.TakePicture()`) with FileProvider URIs (`cache/images/temp_capture_*.jpg`), camera runtime permission check with rationale dialog, real gallery selection (`ActivityResultContracts.GetContent("image/*")`), persistent "Change photo" and "Remove photo" actions, plus preserved sample presets for demo testing.
  - *Non-Blocking Quality Guidance*: Background simulated evidence verification without predictive or misleading AI classifications.
  - *Citizen-Selected Category & Quick Phrases*: Citizen directly selects issue category from clear prompt ("What is the issue about?"). Includes approved quick phrases ("Large pothole on the road", "Garbage has been dumped here", "Water is leaking continuously", "Streetlight is not working", "Road is damaged and difficult to use") with intelligent punctuation-aware appending and 300-character constraint.
  - *Location Acquisition Strategy*: Ordered strategy checking permissions $\to$ location services (GPS/network) $\to$ fast cached `lastLocation` (< 5 mins) $\to$ fresh fused `getCurrentLocation` (10s timeout) $\to$ active `LocationRequest` callback with lifecycle cleanup $\to$ platform `LocationManager` fallback. Immediate coordinate recording (`COORDINATES_FOUND`) followed by non-blocking async `Geocoder` reverse geocoding (`ADDRESS_RESOLVING` $\to$ `RESOLVED`). Geocoding failures never discard valid coordinates.
  - *Google Map Preview & Fixed Center-Pin Selector*: Google Maps Compose integration featuring a center-pin map picker (map moves beneath a fixed center pin, camera idle updates coordinates debounced 500ms, async reverse geocoding). Graceful, transparent fallback info card when `MAPS_API_KEY` is unconfigured (no fake maps or crashes). Supports manual address/PIN entry fallback with distinct `LocationSource` attribution (`CURRENT_LOCATION`, `MAP_SELECTION`, `MANUAL`).
  - *Draft Dirty State & Discard Protection*: Dirty state tracking (`isDraftDirty()`) activates only when meaningful input is entered (image, description, non-default category, or location). Intercepts back navigation to show a Discard Confirmation Dialog ("Keep editing" / "Discard draft").
  - *Report Identifiers*: Uses standard format `CS-DEMO-XXXXX` with random numbers.
- **Home Screen Greeting**: Dynamic time-based greeting (`calculateGreeting`) adjusting by time of day (05:00–11:59 Good morning, 12:00–16:59 Good afternoon, 17:00–20:59 Good evening, 21:00–04:59 Welcome back; safe fallback "Welcome back" if blank name).
- **Launcher & Adaptive Icons**: The Civic Path mark is the single CivicSense brand identity. `ic_launcher` uses Android adaptive icon resources (`mipmap-anydpi-v26`/`ic_launcher.xml`) with the Civic Path foreground (`mipmap-xxxhdpi/ic_launcher_foreground.png`), pale sage background color `#E4ECE1` (`color/ic_launcher_background`), Android 13+ themed monochrome layer (`mipmap-anydpi-v33`/`ic_launcher.xml` + white-silhouette `mipmap-xxxhdpi/ic_launcher_monochrome.png`), and round-icon variants. `AndroidManifest` references `@mipmap/ic_launcher` / `@mipmap/ic_launcher_round`. The launcher logo artwork is scaled ~40% smaller than the original export (foreground art ≈151/432px vs 249/432px), centered on the unchanged 432×432 transparent canvas with expanded safe-zone spacing. Complete-icon backgrounds were unified to `#E4ECE1`. The old map-pin brand vector (`drawable/ic_civicsense_logo.xml`) was removed entirely; the splash theme, Compose splash, and in-app image-placeholder fallbacks now use `drawable/ic_civicsense_path_logo.xml` — a VectorDrawable derived from the master Civic Path SVG (viewBox 580, forest green `#556A54` / charcoal `#2A3328`).
- **Data & Mock Layer**: Centralized `ReportRepository` singleton holding observable reports (`StateFlow`), seed reports covering all civic categories, and dynamic submission updates that immediately reflect across Home and My Reports.
- **Automated Verification**: 29 unit tests across `AppThemeTest`, `NavigationDestinationsTest`, `ReportRepositoryTest`, `ReportViewModelTest`, and `ValidationTest` (100% pass rate). Debug APK builds and packages cleanly (`assembleDebug`).

### Mobile Client (React Native / Expo Scaffold)

**Status:** Implemented (Phase 0 Scaffold)

- Built with Expo SDK 52 and React Native in strict TypeScript mode.
- Feature-oriented directory structure (`mobile/src/features/reports/`, `mobile/src/core/`, `mobile/src/shared/`).
- `ApiClient`: Typed HTTP client with configurable `EXPO_PUBLIC_API_BASE_URL`, request timeout handling via `AbortController`, client-side `X-Request-ID` generation, and structured API error parsing.
- `ReportCreateScreen`: Validates citizen problem description (minimum 3 characters), displays attached GPS coordinates via `LocationPickerStub`, displays attached evidence placeholder, and executes submission.
- `ReportDetailScreen`: Displays tracking ID, lifecycle status badge, coordinates, description, and timeline.
- State-driven navigation in `App.tsx` between submission and detail views.
- Icon configuration wired into `app.json` (Expo SDK 52): `icon` (1024×1024 full-color on `#E4ECE1` background), `android.adaptiveIcon.foregroundImage` (Civic Path, ~40% smaller launcher artwork), `backgroundColor #E4ECE1`, and `monochromeImage` (themed icon). `mobile/assets/` contains the generated Civic Path PNGs (`icon.png`, `adaptive-icon.png`, `monochrome.png`, `splash-icon.png`, `favicon.png`).

### Web Dashboard (React + Vite Admin Portal)

**Status:** Implemented (Phase 1 Production Web Application)

- **Platform & Toolchain**: React 18.3.1, TypeScript 5.6, Vite 5.4, Tailwind CSS 3.4, TanStack Query v5, Recharts 2.15, Leaflet 1.9, React Leaflet 4.2, Vitest 2.1, Node v24.14.0. Google Maps JS API (key `VITE_GOOGLE_MAPS_API_KEY`, same key as Android `MAPS_API_KEY`). `@types/google.maps` registered in `tsconfig.json` types.
- **Directory**: `dashboard/` with root entrypoint `src/main.tsx` and application shell `src/App.tsx`.
- **Brand Continuity & Design**: Built following Apple Design principles (`.agents/skills/apple-design/SKILL.md`) and strict CivicSense brand colors. Civic Path SVG mark (`CivicSenseLogo`) displayed in sidebar header, topbar (mobile), browser tab title, and `index.html` favicon links.
- **Sidebar (Aceternity hover-expand pattern)**: `Sidebar.tsx` rebuilt following the Aceternity design system. Desktop: 68px icon-only by default → smoothly expands to 280px on hover (spring `[0.16, 1, 0.3, 1]`, 280ms). Mobile: full-height slide-in drawer at 280px with backdrop overlay. Both use `SidebarContext` (open/setOpen/animate). NavLink active state uses `civic-green/15` container style. Officer name + logout icon visible in expanded footer. No pin/lock toggle — purely hover-driven. Nav sections: Operations (Overview, Reports Queue, AI Operations, Live Map, Analytics) + Administration (Departments, Staff & Roles, Settings).
- **Topbar**: Rebuilt with `useRef` + `useEffect` outside-click handlers closing both theme and profile dropdowns on any external click. Escape key also dismisses both. Dropdowns animated with `AnimatePresence` (opacity+scale+y spring). Theme dropdown shows checkmark on active selection. Profile menu renders correct dark-mode neutral colors throughout. Logout navigates to `/login`.
- **AppShell**: Uses route-keyed `AnimatePresence mode="wait"` for cross-page fade+slide transitions (0.25s). Automatically closes mobile drawer on route change. Background updated to `neutral-50/950` to match Aceternity palette.
- **Dark Mode**: Systematic color rework — sidebar and topbar now use `neutral-100/neutral-900` palette (matching Aceternity). All dropdown menus use `neutral-800` dark background with `neutral-200` text. Skeleton loading updated to match new sidebar width (68px icon-only). `index.css` adds `animate-in`, `fade-in`, `zoom-in-95` keyframe utilities.
- **Entry Animations**: All pages (ReportsPage, ReportDetailPage, AnalyticsPage, AIOperationsPage, MapPage, DepartmentsPage, UsersPage, SettingsPage) use staggered Apple-spring container/item variants (`ease: [0.16, 1, 0.3, 1]`, stagger 0.06s). Plus cross-page route transition animation in AppShell.
- **Map**: Google Maps JS API replaces Leaflet as primary map provider via `GoogleMapsProvider.tsx`. `MapRenderer.tsx` defaults to `preferredProvider='google-maps'`. Leaflet retained as offline fallback. Custom SVG severity-colored pins. `ReportDetailPage` uses `MapRenderer` for single-report location.
- **Explicit Data Boundary**: Startup environment validator (`src/core/config/env.ts`) enforcing explicit `VITE_DATA_MODE` (`mock` or `api`). `googleMapsApiKey` exposed with Android key default.
- **Data Access & State Machine**:
  - `IReportRepository` contract with `MockReportRepository` and `ApiReportRepository` (FastAPI REST integration).
  - Strict server-authoritative lifecycle state machine matching backend across 11 canonical states.
  - TanStack Query mutations with query key cache invalidation.
  - Direct closures/rejections mandate structured `ClosureReason` + officer justification.
- **Operational Screens**: OverviewPage, ReportsPage, ReportDetailPage (full operations workspace), MapPage (Google Maps + accessible list toggle), AnalyticsPage (honest operational metrics), DepartmentsPage, UsersPage, SettingsPage (reflects Google Maps config).
- **Authentication & Governance**: Mock officer session with role-based personas, `ProtectedRoute` guard, and `can(user, action)` permission checks.
- **Verification**: 34 passing unit and integration tests (`npm run test`), 0 TypeScript errors (`npm run typecheck`), optimized production bundle (`npm run build`).


---

## 3. Backend

**Status:** Implemented (Phase 0 Foundation & Lifecycle Operations)

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
  - `PATCH /api/v1/reports/{identifier}/transition`: Safely advances report lifecycle status according to canonical state machine rules with optional reason, notes, and actor metadata.
  - `POST /api/v1/reports/{identifier}/verify`: Submits human review verdict (`CONFIRMED`, `CORRECTED`, `REJECTED`, `DUPLICATE`), persists `Verification` record, and advances lifecycle to `VERIFIED` or `CLOSED`.
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

## 5. AI / ML Pipeline & Operations Center

**Status:** Implemented (Phase 1.5 Deterministic Demo Processor & Persistent Operations Architecture)

- **Honest AI Boundary**: Runs a deterministic, prototype multimodal inference pipeline (`DeterministicDemoProcessor`) labeled transparently across all API responses and UI cards as `CivicSense Prototype AI (Deterministic Demo Processor) / Demo Simulation`. Does not falsely claim deep learning neural networks, GPU compute, or opaque black-box models exist.
- **8-Stage Sequential Topology**:
  1. `INTAKE_VALIDATION`: Schema validation, media presence, tamper-evident hash calculation (`sha256`), GPS range validation.
  2. `PREPROCESSING`: Normalization, EXIF verification, text sanitization, tokenization.
  3. `VISION_ANALYSIS` (`PrototypeVisionAnalyzer`): Defect surface detection heuristic based on media evidence, computing visual category, visual severity, and visual confidence.
  4. `TEXT_ANALYSIS` (`PrototypeTextPatternAnalyzer`): Keyword pattern matching and civic vocabulary extraction with urgency signal detection.
  5. `FUSION` (`PrototypeFusionEngine`): Cross-modal alignment, calculating modality agreement score ($0.0 - 1.0$), detecting category/severity conflicts.
  6. `DECISION` (`PrototypeDecisionEngine`): Deterministic synthesis of final category, physical severity, operational dispatch priority (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), and SLA estimate.
  7. `HUMAN_REVIEW` (Confidence Gate): Automated threshold evaluation. If `confidence < 0.70` or `modality_agreement < 0.60`, sets `review_required = True`, `current_stage = HUMAN_REVIEW`, `status = COMPLETED`, and transitions report status to `VERIFICATION_REQUIRED`. If thresholds pass, sets `review_required = False`, `current_stage = COMPLETED`, and transitions report to `AI_PROCESSED`.
  8. `COMPLETED`: Emits completion event, durably writes `AIAnalysis` and `AIJobEvent` rows to database, and triggers municipal triage handoff.
- **Persistence & Immutability**:
  - `ai_jobs` table stores job execution lifecycle (`QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`, `CANCELLED`), current stage, review requirements, execution mode, worker ID, and timestamps.
  - `ai_job_events` table stores sequential audit log rows per stage with start/completion times, execution duration (ms), stage status, and structured metadata JSON.
- **AI Operations Center (`/ai-operations`)**:
  - Dedicated web dashboard operations console displaying 8-stage conveyor belt topology, active jobs filter, persisted event stream timeline, honest operational metrics (with `INSUFFICIENT_DATA` handling), and worker health.
- **Report Detail AI Integration**:
  - State-aware AI panel displaying live pipeline progression, Vision vs. Text breakdown, modality agreement %, human review rationale callout, and side-by-side Human Verification vs. AI proposal comparison.
  - No manual completion bypass in API mode; real jobs execute and persist server-side.

---

## 6. Edge / On-Device Processing

**Status:** Not Implemented

- Mobile client currently captures text descriptions, photos, and GPS coordinates as input data. On-device image preprocessing, quality estimation, and lightweight local ML runtimes (ONNX/LiteRT) are deferred to subsequent sprints.

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
- **Phase 1 Native Android Prototype**: Implemented comprehensive Jetpack Compose citizen app prototype with Material 3 design, multi-step report wizard, DataStore profile persistence, and localized state flow.
- **Phase 1.2 Android UX & Polish**: Integrated real device capabilities (camera `TakePicture` with FileProvider, gallery `GetContent`, `FusedLocationProviderClient` with `LocationManager` fallback, async `Geocoder`), strict input normalization, app-wide dark/light theme switching, dirty-draft discard dialogs, honest category choices (including "Not sure"), removed fake maps and misleading AI labels, and enforced robust back-stack navigation.
- **Phase 1 Web Dashboard**: Implemented production-grade React 18.3 + TypeScript + Vite authority web portal (`dashboard/`). Built around Apple Design principles with calm, data-dense interfaces, strict CivicGreen brand palette, server-authoritative lifecycle state machine (matching backend `ReportLifecycleManager`), explicit data mode boundary (no silent mock fallback), Leaflet geospatial maps with accessible table fallback, honest AI governance metrics, and 24 passing unit/integration tests.

---

## 10. Current Implementation State

- **Backend**: Fully functional FastAPI service with 34 passing automated tests (`pytest`) covering unit, integration, API, and runtime matrix cases (A–G), strict type checking (`mypy`), zero lint/format issues (`ruff`), Alembic migrations `0001` and `0002`, verified persistent AI Operations REST API (`/api/v1/ai/*`, `/api/v1/reports/{id}/ai/*`), and closed-loop human verification completion with audit events.
- **Android App**: Fully functional Jetpack Compose Phase 1.3 implementation with 29 passing unit tests (`gradle testDebugUnitTest`), debug APK assembled (`android/app/build/outputs/apk/debug/app-debug.apk`), official Material 3 PullToRefreshBox, DataStore persistence, real camera/location device integration, and end-to-end report wizard navigation.
- **Web Dashboard**: Fully functional React 18.3.1 + Vite + TypeScript application with 34 passing unit/integration tests across 7 test suites (`npm run test`), 0 TypeScript errors (`npm run typecheck`), optimized production bundle (`npm run build`), dedicated `/ai-operations` pipeline console, state-aware Report Detail AI cards, Map provider abstraction, and explicit API/mock mode switching.
- **Database**: PostgreSQL 16 Docker Compose configuration with versioned Alembic migrations (`0001_initial_civicsense_schema.py` and `0002_ai_jobs_and_events.py`).
- **Mobile Scaffold**: React Native + Expo client with zero TypeScript compiler errors (`tsc --noEmit`), typed API client, and report submission/detail UI.
- **Contracts**: Shared JSON schema (`shared/schemas/report_submission.json`) defining the edge-to-cloud report submission contract.
