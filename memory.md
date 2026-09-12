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
- **Entry & Onboarding Lifecycle**:
  - Deterministic 4-state onboarding engine (`OnboardingState`: `LOADING`, `NEEDS_BOARDING`, `NEEDS_PROFILE`, `READY`).
  - Strict profile validation (`UserProfile.isProfileValid`) requiring both valid full name and normalized 10-digit Indian mobile before granting Home access. Incomplete profiles automatically route to Profile Setup.
  - `SplashScreen` features a single-dispatch navigation guard (`hasNavigated`) preventing race conditions, duplicate navigation, and premature Home flashes during DataStore loading.
  - Backup protection: Configured `allowBackup="false"`, `dataExtractionRules.xml`, and `backup_rules.xml` (targeting Android 12+ / API 35) to permanently prevent Android Auto Backup from restoring stale DataStore preferences across uninstalls and reinstalls.
  - Android SplashScreen API integration, 3-slide `HorizontalPager` onboarding with page indicators, and local profile setup.
- **Profile Setup & Input Placeholders**: Simplified phone placeholder to strictly `9874563210` with persistent label and helper text (`10-digit Indian mobile number`). Realistic input placeholders across all screens: name (`Abhishek S`), locality (`Near the public library, Main Road`), PIN (`695xxx`), description (`Describe what happened...`). Strict Indian mobile normalization (strips `+91` or 12-digit `91`, requires 10 digits starting with 6, 7, 8, or 9; no naive `takeLast(10)`), 6-digit postal PIN validation, and a brief 700ms completion screen before entering the dashboard.
- **Citizen Contact Information in Reports**:
  - Transmits full citizen identity (`citizen_name`, `citizen_phone`, `citizen_email`, `citizen_postal_code`) from persisted DataStore profile via `ProcessedReportPackage`, `CivicSenseEdgeProcessor`, and `CivicReportUploadClient`.
  - Privacy-safe diagnostic logging (`HTTP_REQUEST_AUDIT`) tracks presence flags (`citizen_name_present`, `citizen_phone_present`, `citizen_email_present`, `citizen_postal_code_present`) and byte counts without logging private personal values.
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
  - *Report Identifiers*: Uses standard format `CS-DEMO-XXXXX` with random numbers for local demo state, or backend-assigned `REP-YYYYMM-XXXXXX` upon network submission, falling back to `CS-OFFLINE-XXXXX` when queued offline.
  - *Edge Preprocessing & Upload Pipeline (Phase 1)*: `CivicSenseEdgeProcessor` executes non-deep-learning client preprocessing (image metadata sanitization, EXIF stripping, preview downscaling, blur/brightness heuristic, keyword extraction). `CivicReportUploadClient` packages evidence with `edge_metadata` and uploads via OkHttp with bounded exponential backoff (3 retries). Base URL is dynamically configurable via `local.properties` (`API_BASE_URL`), injected into `BuildConfig.API_BASE_URL` with safe fallback to emulator (`10.0.2.2:8000`). Structured diagnostic logging (`CivicSenseSubmit`) instruments the full submission lifecycle (`SUBMIT_START`, `IMAGE_PREP_*`, `FEATURE_EXTRACTION_*`, `REQUEST_BUILD_*`, `HTTP_REQUEST_*`, `HTTP_RESPONSE`, `RETRY_START`, `OFFLINE_FALLBACK`, `SUBMIT_END`).
  - *Offline State Semantics & UI Lifecycle*: Offline queueing explicitly sets `SubmissionState.QUEUED_OFFLINE` and `ReportStatus.QUEUED_OFFLINE`. UI renders "Report saved on this device" with "Local Reference" label. `ReportViewModel.submitReport` guarantees `isSubmitting = false` via strict `try / catch / finally` preventing indefinite hang states. Note: WorkManager background sync is not yet implemented; reports remain in device session memory until persistent queueing is introduced.
- **Home Screen Greeting**: Dynamic time-based greeting (`calculateGreeting`) adjusting by time of day (05:00–11:59 Good morning, 12:00–16:59 Good afternoon, 17:00–20:59 Good evening, 21:00–04:59 Welcome back; safe fallback "Welcome back" if blank name).
- **Launcher & Adaptive Icons**: The Civic Path mark is the single CivicSense brand identity. `ic_launcher` uses Android adaptive icon resources (`mipmap-anydpi-v26`/`ic_launcher.xml`) with the Civic Path foreground (`mipmap-xxxhdpi/ic_launcher_foreground.png`), pale sage background color `#E4ECE1` (`color/ic_launcher_background`), Android 13+ themed monochrome layer (`mipmap-anydpi-v33`/`ic_launcher.xml` + white-silhouette `mipmap-xxxhdpi/ic_launcher_monochrome.png`), and round-icon variants. `AndroidManifest` references `@mipmap/ic_launcher` / `@mipmap/ic_launcher_round`. The launcher logo artwork is scaled ~40% smaller than the original export (foreground art ≈151/432px vs 249/432px), centered on the unchanged 432×432 transparent canvas with expanded safe-zone spacing. Complete-icon backgrounds were unified to `#E4ECE1`. The old map-pin brand vector (`drawable/ic_civicsense_logo.xml`) was removed entirely; the splash theme, Compose splash, and in-app image-placeholder fallbacks now use `drawable/ic_civicsense_path_logo.xml` — a VectorDrawable derived from the master Civic Path SVG (viewBox 580, forest green `#556A54` / charcoal `#2A3328`).
- **Citizen Remote Report Synchronization & Ownership Layer**:
  - *Installation-Scoped Ownership (`citizen_id`)*: Generated once using UUIDv4 (`"czn_" + UUID.randomUUID()`) and persisted in Android DataStore via `PreferenceRepository.getOrCreateCitizenId()`. Submitted report tracking IDs are recorded in `submitted_report_ids` preference set. Transmitted on submission and used to scope remote report queries. (Clearly isolated as a prototype ownership token without pretending to be full authentication).
  - *Remote Data Source (`RemoteReportsDataSource`)*: Implements `ReportsDataSource` via OkHttp, executing non-blocking network calls on `Dispatchers.IO`. Queries `GET /api/v1/reports?citizen_id=...&page_size=50` and `GET /api/v1/reports/{identifier}`. Configured dynamically with `API_BASE_URL`.
  - *Pure Server-to-Citizen Status & Timeline Mapper (`ReportStatusMapper`)*:
    - Pure functional mapping from all 11 backend server statuses to 7 citizen-facing statuses (`SUBMITTED` $\to$ `SUBMITTED`; `AI_PROCESSING`, `AI_PROCESSED`, `VERIFICATION_REQUIRED` $\to$ `UNDER_REVIEW`; `VERIFIED`, `PRIORITIZED` $\to$ `CONFIRMED`; `ASSIGNED` $\to$ `ASSIGNED`; `IN_PROGRESS` $\to$ `IN_PROGRESS`; `RESOLVED`, `RESOLUTION_VERIFIED` $\to$ `RESOLVED`; `CLOSED` $\to$ `CLOSED`).
    - Dynamic 6-Stage Resolution Timeline (`buildTimeline`): Derives completed and active stages with citizen-friendly descriptions and formatted ISO-8601 timestamps (using `java.time`). Stage 4 displays the specific assigned department (`"Assigned to [Department Name]."`). When department reassignment is in progress (`reassignment_required=true` returning to `PRIORITIZED`), Stage 3 displays `"Triage team is reassigning issue to the appropriate division."` without confusing or alarming the citizen.
    - Department & Reassignment Tracking: `Report` domain model holds `assignedDepartment` and `reassignmentRequired` fields parsed from server responses.
    - Severity and Category Translation: Maps priority/AI severity to UI `IssueSeverity`, and backend string categories to `ReportCategory` enums with safe fallbacks.
    - Media URL Resolution: Prepend backend base URL to relative evidence `/uploads/...` paths so Coil `AsyncImage` renders server-stored photos directly on Android.
  - *Repository Cache & Merge Invariants*:
    - `ReportRepository` merges fetched remote reports by replacing stale cached entries while strictly preserving uncommitted `QUEUED_OFFLINE` reports.
    - Detail fetch via `fetchReportDetail(identifier)` updates the single report in the repository cache and returns the refreshed entity.
    - Updated `ReportFilter.RESOLVED` to include both `RESOLVED` and `CLOSED` statuses.
  - *Lifecycle-Aware, Visibility-Aware Smart Polling Synchronization*:
    - `MyReportsScreen`: Automatic silent polling every 10 seconds (`MY_REPORTS_POLL_INTERVAL_MS = 10_000L`) using `repeatOnLifecycle(Lifecycle.State.RESUMED)`. Updates the backing `StateFlow` silently without activating the pull-to-refresh spinner. Automatically pauses when the app is backgrounded (`ON_PAUSE`) and cancels when navigating away. Catches network dropouts cleanly without disruptive UI errors.
    - `ReportDetailScreen`: Automatic silent single-report polling every 6 seconds (`REPORT_DETAIL_POLL_INTERVAL_MS = 6_000L`) while visible and `RESUMED`, silently updating active view state and resolution timeline.
    - `ReportRepository`: Cache update returns existing reference when data is unchanged, eliminating unnecessary StateFlow emissions and Compose recompositions. Preserves `QUEUED_OFFLINE` reports and prevents concurrent duplicate fetch requests.
  - *Pull-to-Refresh & Lifecycle Triggers*:
    - `MyReportsScreen`: Automatic initial remote fetch on first composition and manual pull-to-refresh fallback via Material 3 `PullToRefreshBox`.
    - `ReportDetailScreen`: Pull-to-refresh integration via Material 3 `PullToRefreshBox` with `onRefreshDetail` callback executing single-report remote fetch and updating local view state.
    - NavHost triggers background refresh on navigating to `AppDestinations.MAIN`.
- **Data & Mock Layer**: Centralized `ReportRepository` singleton holding observable reports (`StateFlow`), pluggable `ReportsDataSource` abstraction (`RemoteReportsDataSource` wired in `MainActivity`, with `LocalReportsDataSource` fallback), seed reports covering all civic categories, and dynamic submission updates that immediately reflect across Home and My Reports.
- **Automated Verification**: Comprehensive unit test coverage across `AppThemeTest`, `NavigationDestinationsTest`, `ReportRepositoryTest`, `ReportViewModelTest`, `ValidationTest`, `CivicSenseEdgeProcessorTest`, `CivicReportUploadClientTest`, `ReportStatusMapperTest`, `RemoteReportsDataSourceTest`, and `PollingSyncTest` (100% pass rate: 74 tests passing, including UTC and naive timestamp mapping). Debug APK builds and packages cleanly (`assembleDebug`).

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
  - TanStack Query mutations with query key cache invalidation and immediate local UI updates.
  - Direct closures/rejections mandate structured `ClosureReason` + officer justification.
- **Near-Real-Time Smart Polling Synchronization**:
  - `ReportsPage`: Configured with `refetchInterval: 5000` (5s), `refetchIntervalInBackground: false`, and `refetchOnWindowFocus: true`. Automatically keeps the queue fresh while active and pauses when the browser tab is hidden. Preserves active filters, sorting, and scroll position without full-page loading indicators. Includes Department filter dropdown.
  - `ReportDetailPage`: Configured with `refetchInterval: 4000` (4s), `refetchIntervalInBackground: false`, and `refetchOnWindowFocus: true` for the active report.
  - `OverviewPage`: Configured with `refetchInterval: 10000` (10s) on statistics and urgent report queues.
  - `MapPage`: Configured with `refetchInterval: 15000` (15s) on map points with stabilized initial center, preventing map viewport jumps.
  - `DepartmentsPage` and `DepartmentDetailPage`: Configured with `refetchInterval: 5000` (5s) for live workload metrics and department job queue.
  - Local mutations immediately update query cache and invalidate queries without waiting for the next polling interval.
- **Department Operations Workflow**:
  - `DepartmentsPage`: Real-time TanStack Query fetching municipal divisions with live metrics (In Progress, Pending Acknowledgment, Resolved, Total, and Declined/Reassignment Required warning). Cards navigate to `/departments/:code`.
  - `DepartmentDetailPage` (`/departments/:id`): Operational division workspace with department header (contact info, SLA target, lead officer), 5-metric workload stats row, status tabs (`ALL`, `ASSIGNED` [Pending Acknowledgment], `IN_PROGRESS`, `RESOLVED`), and interactive job queue.
  - Job Actions: In-table and detail actions for "Acknowledge Job" (transitions `ASSIGNED` $\to$ `IN_PROGRESS`), "Decline Job & Return to Triage" (opens structured rejection modal with reason and notes), and "Complete Job" (opens completion modal with required remediation notes).
  - Triage Alerts & Reassignment: Prominent "Department Reassignment Required" warning banner on `ReportDetailPage` when `reassignmentRequired === true`.
  - Audit Trail: Immutable "Department Assignment History" card rendering historical assignment lifecycle (`ASSIGNED`, `IN_PROGRESS`, `COMPLETED`, `REJECTED`) with officer, timestamps, rejection reasons, and completion notes.
- **Operational Screens**: OverviewPage, ReportsPage, ReportDetailPage (full operations workspace), MapPage (Google Maps + accessible list toggle), AnalyticsPage (honest operational metrics), DepartmentsPage (live directory), DepartmentDetailPage (job operations queue), UsersPage, SettingsPage (reflects Google Maps config).
- **Evidence Media & Citizen Privacy**:
  - `resolveMediaUrl(uri)`: Normalizes relative `/uploads/...` and bare filenames to absolute backend origin URLs, preserving full HTTPS/data URIs.
  - `ReportDetailPage`: Renders report evidence images with loading skeletons and broken image fallback handling.
  - Authorized "Citizen Reporter Information" card renders citizen name and phone number with "Authorized View Only" badge and privacy disclaimer, restricting contact info to triage officers without leaking to public feeds.
- **Accurate Timestamps & Localization**:
  - `dateUtils.ts`: Centralized UTC parsing and localization suite (`parseUtcDate`, `normalizeIsoUtc`, `formatDateShort`, `formatDateTime`, `formatDateFull`, `formatTime`, `formatRelativeTime`).
  - Strict UTC ISO parsing: Automatically detects ISO date-time strings without explicit `Z` or timezone offsets and ensures they are parsed as true UTC rather than being distorted into browser local time by ECMAScript defaults.
  - `ReportsPage` renders a two-line submitted timestamp (`Sep 12 • 03:37 PM` + relative `5m ago`) with full ISO/local tooltip on hover.
  - `ReportDetailPage` formats submission date, last modified date, SLA deadline, operational notes, and audit history accurately in local time.
- **Authentication & Governance**: Mock officer session with role-based personas, `ProtectedRoute` guard, and `can(user, action)` permission checks.
- **Verification**: 59 passing unit and integration tests across 11 test files (`npm run test`), 0 TypeScript errors (`npm run typecheck`), optimized production bundle (`npm run build`).


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
  - `POST /api/v1/reports`: Ingests citizen report with optional `citizen_name`, `citizen_phone`, and `edge_metadata` contract (versioned client processing flags, image quality metrics, text features). Decodes client base64 evidence image payloads (`data_base64`), persists binary to disk (`uploads/rep_{report_id}_{uuid}.jpg`), generates SHA-256 hash, and sets public browser `storage_uri` to `/uploads/...`. Assigns human-readable tracking ID (`REP-YYYYMM-XXXXXX`), initializes status to `SUBMITTED`, persists attached evidence references, and returns 201 Created. Fully supports idempotency via `client_report_id` and `X-Idempotency-Key`, safely replaying existing records with `200 OK` and `X-Idempotent-Replay: true`.
  - `GET /uploads/{filename}`: Static file mount (`app.mount("/uploads", StaticFiles(directory=settings.UPLOADS_DIR))`) serving persisted evidence images to dashboard and mobile clients.
  - `GET /api/v1/reports`: Paginated list of reports sorted descending by creation time. Supports optional `citizen_id` query parameter (`GET /api/v1/reports?citizen_id=...`) to filter reports strictly to the citizen's installation token. Citizen/public callers receive masked contact details (`citizen_phone`, `citizen_email`, `citizen_postal_code` masked to `None`), while omitting `citizen_id` preserves full unfiltered report feeds for authorized dashboard triage.
  - `GET /api/v1/reports/stats`: Aggregated intake and triage metrics (`totalReports`, `pendingReview`, `inProgress`, `resolvedToday`, `criticalIssues`, `avgResolutionDays`, `aiAgreementRate`) with camelCase aliases for dashboard consumption, registered prior to `/{identifier}` to avoid route shadowing.
  - `GET /api/v1/reports/{id}`: Retrieves single report by internal UUID or tracking ID, including `citizen_name`, `citizen_phone`, and evidence storage URIs.
  - `PATCH /api/v1/reports/{identifier}/transition`: Safely advances report lifecycle status according to canonical state machine rules with optional reason, notes, and actor metadata. Synchronizes `ReportAssignment` records automatically when advancing to `ASSIGNED`, `IN_PROGRESS`, or `RESOLVED`.
  - `POST /api/v1/reports/{identifier}/verify`: Submits human review verdict (`CONFIRMED`, `CORRECTED`, `REJECTED`, `DUPLICATE`), persists `Verification` record, and advances lifecycle to `VERIFIED` or `CLOSED`.
  - `GET /api/v1/departments`: Lists active municipal departments with calculated workload metrics (`stats`).
  - `GET /api/v1/departments/{identifier}`: Retrieves single department by UUID or uppercase short code (e.g. `ROADS`, `WASTE`).
  - `GET /api/v1/departments/{identifier}/stats`: Retrieves operational workload stats (`total_assigned`, `pending_acknowledgment`, `in_progress`, `resolved`, `rejected_assignments`, `reassignment_required`).
  - `GET /api/v1/departments/{identifier}/reports`: Retrieves paginated reports assigned to the specified department with status/priority filtering.
  - `POST /api/v1/reports/{id}/assign`: Assigns report to a department, creates `ReportAssignment` audit record (`AssignmentStatus.ASSIGNED`), sets `Report.status = ASSIGNED`, and resets `reassignment_required = False`.
  - `POST /api/v1/reports/{id}/acknowledge`: Department acknowledges job order, updates assignment status to `IN_PROGRESS`, and transitions report status to `IN_PROGRESS`.
  - `POST /api/v1/reports/{id}/complete`: Records field remediation report (`resolver_notes`), updates assignment to `COMPLETED`, and transitions report to `RESOLVED`.
  - `POST /api/v1/reports/{id}/department-reject`: Department declines work ticket with structured rejection reason (`OUT_OF_JURISDICTION`, `INSUFFICIENT_ACCESS`, `DUPLICATE_WORK_ORDER`, `REQUIRES_MAJOR_BUDGET`, `INSUFFICIENT_INFORMATION`, `OTHER`) and justification notes. Updates assignment to `REJECTED`, transitions report status from `ASSIGNED` back to `PRIORITIZED`, flags `reassignment_required = True`, but preserves `Report.department` for triage auditability.
  - `GET /api/v1/reports/{id}/assignments`: Retrieves immutable assignment audit history for a report.
- **Report Lifecycle Engine**: `ReportLifecycleManager` enforces valid transitions across 11 explicit states (`SUBMITTED`, `AI_PROCESSING`, `AI_PROCESSED`, `VERIFICATION_REQUIRED`, `VERIFIED`, `PRIORITIZED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `RESOLUTION_VERIFIED`, `CLOSED`). `CLOSED` is enforced as a terminal state.
- **Strict UTC Serialization**: Pydantic v2 schemas (`ReportRead`, `AIAnalysisRead`, `VerificationRead`, `EvidenceRead`, `IssueRead`, `DepartmentRead`, `AssignmentRead`) use `ensure_utc` validator and serializer guaranteeing that all naive and aware database timestamps serialize to standard ISO 8601 UTC with explicit `Z` suffix (e.g. `2026-09-12T10:07:04.321792Z`). Eliminates client-side ECMAScript timezone shifting bugs.

---

## 4. Database

**Status:** Implemented (Schema & Migrations)

- **Engine & Dialect**: PostgreSQL 16 (psycopg 3 driver) with fallback compatibility for SQLite in isolated automated tests.
- **ORM**: Modern SQLAlchemy 2.0 with strict `Mapped[T]` and `mapped_column()` typing.
- **Migrations**: Alembic with versioned migrations:
  - `0001_initial_civicsense_schema.py`: complete core relational schema, foreign keys, and indexes.
  - `0002_ai_jobs_and_events.py`: AI operations tracking (`ai_jobs`, `ai_job_events`) and report routing assignments.
  - `0003_add_edge_metadata.py`: adds `reports.edge_metadata` JSON column for client edge preprocessing provenance.
  - `0004_add_citizen_name_phone.py`: adds `reports.citizen_name` (VARCHAR 128) and `reports.citizen_phone` (VARCHAR 32) columns.
  - `0005_add_citizen_email_postal_code.py`: adds `reports.citizen_email` (VARCHAR 255) and `reports.citizen_postal_code` (VARCHAR 32) columns.
  - `0006_add_report_category.py`: adds `reports.category` (VARCHAR 64) column for citizen-selected civic issue categories.
  - `0007_add_departments_and_assignments.py`: adds `departments` and `report_assignments` tables, adds `reports.department_id` foreign key and `reports.reassignment_required` boolean column, and seeds 6 canonical municipal divisions (`ROADS`, `WASTE`, `WATER`, `ELECTRICAL`, `PLANNING`, `PUBLIC_WORKS`).
- **Core Entities & Schema Decisions**:
  - **`Report != Issue`**: `Report` represents an individual citizen submission. `Issue` represents a real-world civic defect on the ground. Multiple reports can map to one issue via foreign key `reports.issue_id`.
  - **Primary Keys**: Internal database IDs use native `UUID`. Citizen-facing tracking IDs are stored separately as unique indexed strings (`tracking_id`).
  - **Departments & Assignments**: `departments` table models municipal operational divisions (`name`, `code`, `head_name`, `contact_email`, `contact_phone`, `sla_hours_default`). `report_assignments` records immutable lifecycle of departmental jobs (`department_id`, `assigned_by`, `assigned_to_officer`, `status`, `rejection_reason`, `notes`, `created_at`, `resolved_at`).
  - **Evidence Preservation**: `evidences` table stores raw asset metadata (`evidence_type`, `storage_uri`, `file_hash`, `mime_type`, `file_size_bytes`, `metadata_json`). Original evidence is preserved and not discarded when representations are generated.
  - **Model Provenance**: `model_versions` table records `model_name`, `model_version`, `preprocessing_version`, `embedding_model`, and `embedding_version`.
  - **Decoupled AI Outputs**: `ai_analyses` table keeps `confidence`, `severity` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `priority` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and `evidence_agreement` in separate independent columns (no monolithic "ai_score").
  - **Audit Tables**: `verifications` records human review verdicts (`CONFIRMED`, `CORRECTED`, `REJECTED`, `DUPLICATE`). `resolutions` records municipal repair completion on an `Issue` without deleting historical defect records.

---

## 4b. Municipal Department Operations Subsystem & System-Wide Influence Matrix

**Status:** Implemented (Phase 1 Municipal Operations & Workflow Orchestration)

### Architectural Role
Central triage officers and AI models do not fix potholes, repair blown streetlights, or clear blocked sewers—operational municipal divisions do. The Municipal Department Operations Subsystem bridges administrative triage and physical ground resolution, governing the real-world operational execution phase of the report lifecycle.

### Domain Entities & Models
1. **`Department` (`app/models/department.py`)**:
   - Canonical registry of municipal operational divisions.
   - Fields: `id` (UUID PK), `name` (VARCHAR 64, unique, indexed), `code` (VARCHAR 32, unique slug, indexed), `description` (TEXT), `head_name` (VARCHAR 128), `contact_email` (VARCHAR 255), `contact_phone` (VARCHAR 32), `sla_hours_default` (Integer default SLA window in hours), `is_active` (Boolean), `created_at` & `updated_at` (timestamptz).
   - Relational mapping: `reports` (1-to-many with `Report`), `assignments` (1-to-many with `ReportAssignment`).
   - Canonical default divisions: `ROADS` (Roads & Bridges, 48h SLA), `WASTE` (Solid Waste Management, 24h SLA), `WATER` (Water Supply & Sewerage, 36h SLA), `ELECTRICAL` (Street Lighting & Electrical, 24h SLA), `PLANNING` (Town Planning & Enforcement, 72h SLA), `PUBLIC_WORKS` (Public Works & Infrastructure, 72h SLA).
2. **`ReportAssignment` (`app/models/assignment.py`)**:
   - Immutable historical audit ledger recording every department dispatch attempt.
   - Fields: `id` (UUID PK), `report_id` (FK `reports.id`, CASCADE), `department_id` (FK `departments.id`, SET NULL), `department_name` (VARCHAR 64 snapshot), `assigned_by` (VARCHAR 128), `assigned_to_officer` (VARCHAR 128), `status` (`AssignmentStatus`: `ASSIGNED`, `IN_PROGRESS`, `COMPLETED`, `REJECTED`), `rejection_reason` (`DepartmentRejectionReason`: `OUT_OF_JURISDICTION`, `INSUFFICIENT_ACCESS`, `DUPLICATE_WORK_ORDER`, `REQUIRES_MAJOR_BUDGET`, `INSUFFICIENT_INFORMATION`, `OTHER`), `notes` (TEXT), `created_at` & `resolved_at` (timestamptz).
   - Relational mapping: `report` (many-to-1 with `Report`), `department` (many-to-1 with `Department`).

### Service Layer Functionalities (`DepartmentService` in `app/services/departments/service.py`)
- **`list_departments(active_only)`**: Fetches all municipal divisions with calculated live workload metrics.
- **`get_department(identifier)`**: Resilient multi-identifier lookup by UUID, uppercase code (`ROADS`), or name.
- **`get_workload_stats(identifier)`**: Real-time aggregation of operational workload metrics: `total_assigned`, `pending_acknowledgment` (`status == ASSIGNED`), `in_progress` (`status == IN_PROGRESS`), `resolved` (`status in [RESOLVED, RESOLUTION_VERIFIED, CLOSED]`), `rejected_assignments` (`ReportAssignment.status == REJECTED`), and `reassignment_required` (`Report.reassignment_required == True`).
- **`get_department_reports(identifier, status, priority, skip, limit)`**: Paginated job queue with status/priority filtering.
- **`assign_report(report_id, department_id, ...)`**: Validates lifecycle transition (`PRIORITIZED` $\to$ `ASSIGNED`), logs immutable `ReportAssignment` with `status = ASSIGNED`, updates `Report.department_id` and `Report.department`, and resets `Report.reassignment_required = False`.
- **`acknowledge_report(report_id, assigned_to_officer, notes)`**: Validates `ASSIGNED` state, transitions `AssignmentStatus` and `ReportStatus` to `IN_PROGRESS`, and records assigned field officer.
- **`complete_report(report_id, resolver_notes, resolved_by)`**: Enforces minimum 5-character remediation notes, marks `AssignmentStatus.COMPLETED`, sets `resolved_at`, and transitions `ReportStatus` to `RESOLVED`.
- **`reject_report(report_id, rejection_reason, notes, suggested_department)`**: Enforces structured reason and justification, marks `AssignmentStatus.REJECTED`, sets `resolved_at`, transitions `ReportStatus` from `ASSIGNED` back to `PRIORITIZED`, flags `Report.reassignment_required = True`, and preserves historical department for triage review.
- **`get_assignment_history(report_id)`**: Retrieves chronological audit trail of all assignment attempts.

### System-Wide Cross-Cutting Influence Matrix

| Domain / Subsystem | Architectural & Functional Influence |
| :--- | :--- |
| **Report Lifecycle & State Machine** | Acts as the operational execution bridge between triage (`PRIORITIZED`) and resolution (`RESOLVED`). Governs transitions `PRIORITIZED` $\to$ `ASSIGNED` $\to$ `IN_PROGRESS` $\to$ `RESOLVED`. Governs the non-destructive rejection loop (`ASSIGNED` $\to$ `PRIORITIZED` with `reassignment_required=True`), ensuring misrouted reports are never closed or lost. |
| **Database & Persistence** | Introduces tables `departments` and `report_assignments`, adds `reports.department_id` foreign key and `reports.reassignment_required` boolean flag (migration `0007`). Preserves immutable audit history across all dispatch, rejection, and completion events. |
| **Web Dashboard (Authority Workflows)** | Powers dedicated `/departments` directory and `/departments/:code` operations workspace with live job queues, status filters, and 5-metric workload counters. Real-time TanStack Query polling (5s) keeps department screens synchronized. Embeds "Department Reassignment Required" warning banners on `ReportDetailPage`. Renders immutable "Department Assignment History" cards detailing officer names, timestamps, rejection reasons, and completion notes. Adds Department filter to global reports queue and map. |
| **Citizen Mobile App (Android & Expo)** | Directly influences citizen status tracking and trust: Stage 4 of the 6-stage resolution timeline displays the assigned municipal division (`"Assigned to [Department Name]."`). If a department declines a ticket (`reassignment_required=True`), Stage 3 transparently informs the citizen (`"Triage team is reassigning issue to the appropriate division."`) without alarming them with internal rejection terminology. Polling sync keeps citizen devices updated in near-real-time. |
| **AI & Decision Engine** | Informs category-to-department routing rules. Informs baseline SLA calculation windows based on `Department.sla_hours_default` (e.g., 24h for Sanitation vs 48h for Roads). Enables human-in-the-loop verification of both category classification and proposed department routing. |
| **Data Mining & Municipal Analytics** | **Cross-Department Defect Interaction**: Identifies systemic inter-departmental root causes (e.g., water pipe leaks weakening sub-base and causing road collapse; or illegal dumping obstructing drainage).<br>**Operational Lead-Time Mining**: Analyzes acknowledgment latency, repair lead times, and SLA breach rates across municipal divisions.<br>**Jurisdictional Ambiguity Mining**: Mining high rejection rates per category pinpoints municipal gray areas (e.g. roadside tree branches between Electrical Dept and Forest/Public Works) requiring policy or classification adjustments. |

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

**Status:** Implemented (Phase 1 Edge Preprocessing & Honest Evidence Packaging Architecture)

- **Android Edge Pipeline** (`com.civicsense.core.edge`):
  - `CivicSenseEdgeProcessor`: Master coordinator executing image preprocessing, text normalization, and evidence contract packaging off the main UI thread with exact millisecond telemetry logging (`[CivicSense][*]`).
  - `CivicImagePreprocessor`: Production-grade Android image preprocessing engine:
    - Memory-safe decoding with power-of-two `inSampleSize` subsampling (`calculateInSampleSize`) protecting against OOM on high-resolution camera captures (tested up to 8000x6000).
    - EXIF orientation inspection and upright matrix correction.
    - Aspect-ratio preserving downscaling to max 640px bounding box (`MAX_PREVIEW_DIMENSION = 640`) for preview generation.
    - Stripping of unnecessary/sensitive device and camera EXIF metadata by recompressing fresh JPEG at 82% quality (`PREVIEW_JPEG_QUALITY = 82`).
    - Deterministic SHA-256 integrity hash calculation across preview file bytes.
    - Fast ITU-R BT.601 perceptual luminance brightness estimation across 32x32 pixel subsamples (`estimateBrightness`).
    - Focus/sharpness gradient estimation (`estimateBlurry`) computing mean variance of adjacent horizontal/vertical pixel luminance differences.
    - Quality threshold evaluation (`determineUsability`) flagging dark (<0.15), overexposed (>0.90), blurry, or low-resolution (<64px) images while allowing user submission with transparent guidance.
    - LRU/TTL preview cache cleanup (`cleanupOldPreviews`) deleting previews older than 2 hours.
  - `CivicTextPreprocessor`: Fast, deterministic edge text normalizer:
    - Trims and collapses irregular multi-whitespace into clean single-spaced strings.
    - Enforces 300-character maximum bounds while calculating character and word counts.
    - Transparent dictionary hint extraction matching keywords against transparent civic vocabularies for severity (`SEVERITY_DICTIONARY`), urgency (`URGENCY_DICTIONARY`), category (`CATEGORY_DICTIONARY`), location (`LOCATION_DICTIONARY`), and safety (`SAFETY_DICTIONARY`).
  - `ProcessedReportPackage`: Canonical versioned data contract (v1.0.0) packaging client report ID, ISO timestamp, location, structured text features, image quality metrics, and client processing flags (`enabled=true`, `processor_version="1.0.0"`, `image_preprocessed`, `text_preprocessed`, `embedding_generated=false`).
  - `CivicReportUploadClient`: Production HTTP client using OkHttp for submitting reports to FastAPI backend (`POST /api/v1/reports`):
    - Packages base64-encoded bytes from client-preprocessed low-resolution preview image (`data_base64`), enabling server-side persistence and media serving without separate multipart endpoints.
    - Ingests citizen contact profile (`citizen_name`, `citizen_phone`) from DataStore (`PreferenceRepository`) and forwards them in root report payload.
    - Emits structured pre-flight diagnostic log (`HTTP_REQUEST_AUDIT`) tracking payload size, preview bytes, and boolean presence flags (`citizen_name_present`, `citizen_phone_present`) without logging private contact details.
    - Bounded exponential backoff retry loop (max 3 attempts, 1000ms base backoff).
    - Immediate failure on non-retryable 4xx client errors without infinite loops.
    - Automatic fallback to offline local queue (`UploadResult.OfflineQueued`) on network dropouts or persistent 5xx server failures.
    - Client tracking and idempotency headers (`X-Client-Report-ID`, `X-Idempotency-Key`).
- **Honest AI Boundary**: Explicitly declares on-device embeddings, TFLite, ONNX, and deep learning neural inference as **NOT enabled** in Phase 1 (`embedding_generated = false`, `embedding = null`).
- **Web Dashboard Provenance Display**: `ReportDetailPage` renders an honest `Client Edge Preprocessing Provenance` card displaying client processor version, preview dimensions, focus/lighting status, normalized word count, extracted linguistic hints, and explicit "On-Device Embeddings: Not Enabled (Phase 1)" badge.

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
- **Phase 1 Edge Processing Architecture**: Built reliable, transparent on-device edge preprocessing across Android (`CivicSenseEdgeProcessor`, `CivicImagePreprocessor`, `CivicTextPreprocessor`, `CivicReportUploadClient`), Backend (`edge_metadata` schema and column, Stage 2 AI demo pipeline provenance, Alembic migration `0003_add_edge_metadata.py`), and Web Dashboard (`Client Edge Preprocessing Provenance` card in `ReportDetailPage`). Strictly declared on-device embeddings as NOT enabled.
- **Phase 1 Municipal Department Operations Subsystem**: Built the complete closed-loop municipal division execution and assignment workflow. Created `Department` and `ReportAssignment` domain models (Alembic migration `0007`), seeded 6 canonical divisions (`ROADS`, `WASTE`, `WATER`, `ELECTRICAL`, `PLANNING`, `PUBLIC_WORKS`), built `DepartmentService` with full operational actions (assign, acknowledge, complete, reject with structured reasons), introduced the non-destructive rejection/reassignment loop (`reassignment_required=true` returning to `PRIORITIZED`), built the React web dashboard department operations hub and job workspace (`/departments`, `/departments/:code`), and wired division-level status transparency into the Android citizen timeline.

---

## 10. Current Implementation State

- **Backend**: Fully functional FastAPI service with 52 passing automated tests (`pytest`) covering unit, integration, API, edge metadata, citizen contact persistence/privacy, category persistence/fallback, UTC timestamp serialization with Z, municipal department lifecycle operations, rejection routing, and runtime matrix cases (A–G), strict type checking (`mypy` - 0 errors across 74 source files with pydantic plugin), zero lint/format issues (`ruff`), Alembic migrations `0001` through `0007`, verified persistent AI Operations REST API (`/api/v1/ai/*`, `/api/v1/reports/{id}/ai/*`), and closed-loop municipal department operations workflow.
- **Android App**: Fully functional Jetpack Compose Phase 1.3 implementation with 76 passing unit tests (`gradle testDebugUnitTest`), debug APK assembled (`android/app/build/outputs/apk/debug/app-debug.apk`), lifecycle-aware silent polling on My Reports (10s) and Report Detail (6s), official Material 3 PullToRefreshBox, DataStore persistence, real camera/location device integration, on-device memory-safe preview generation, EXIF stripping, SHA-256 calculation, focus/brightness estimation, deterministic text normalization, OkHttp upload with full citizen contact transmission (`citizen_name`, `citizen_phone`, `citizen_email`, `citizen_postal_code`) and civic category transmission (`category`), department timeline display, bounded exponential retry and offline fallback queueing, and end-to-end report wizard navigation.
- **Web Dashboard**: Fully functional React 18.3.1 + Vite + TypeScript application with 59 passing unit/integration tests across 11 test suites (`npm run test`), 0 TypeScript errors (`npm run typecheck`), optimized production bundle (`npm run build`), municipal department operations workflow (`DepartmentsPage` directory, `DepartmentDetailPage` queue, Acknowledge, Decline with reason modal, Complete with notes modal, reassignment required alerts, assignment audit trail), near-real-time smart polling across Reports Queue (5s), Detail (4s), Departments (5s), Overview (10s), and Map (15s) with background tab pausing, centralized UTC timestamp parsing and localization (`dateUtils.ts`) preventing timezone offset distortion, dedicated `/ai-operations` pipeline console, state-aware Report Detail AI cards, honest Client Edge Preprocessing Provenance card, authorized Citizen Reporter Information card with contact privacy controls, normalized multi-tier category resolution, Map provider abstraction, and explicit API/mock mode switching.
- **Database**: PostgreSQL 16 Docker Compose configuration with versioned Alembic migrations (`0001_initial_civicsense_schema.py`, `0002_ai_jobs_and_events.py`, `0003_add_edge_metadata.py`, `0004_add_citizen_name_phone.py`, `0005_add_citizen_email_postal_code.py`, `0006_add_report_category.py`, and `0007_add_departments_and_assignments.py`).
- **Mobile Scaffold**: React Native + Expo client with zero TypeScript compiler errors (`tsc --noEmit`), typed API client, and report submission/detail UI.
- **Contracts**: Shared JSON schema (`shared/schemas/report_submission.json`) and Android/FastAPI versioned data contract (v1.0.0) defining the edge-to-cloud report submission contract.
