# CivicSense Mobile Application

Citizen-facing mobile client for **CivicSense — From Citizen Reports to Civic Intelligence**.

## Technology Stack

- **Framework**: React Native with Expo SDK 52
- **Language**: TypeScript (strict mode enabled)
- **Networking**: Typed `ApiClient` with timeout and `X-Request-ID` tracing

## Architecture & Directory Structure

```text
mobile/
├── src/
│   ├── core/
│   │   ├── api/         # Typed ApiClient, endpoints catalogue, error models
│   │   ├── config/      # Environment variables (EXPO_PUBLIC_API_BASE_URL)
│   │   └── utils/       # Safe logging with token/credential redaction
│   ├── features/
│   │   └── reports/     # Report submission feature domain
│   │       ├── components/ # StatusBadge, LocationPickerStub
│   │       ├── hooks/      # useReportSubmission stateful hook
│   │       ├── screens/    # ReportCreateScreen, ReportDetailScreen
│   │       ├── services/   # reportService abstraction
│   │       └── types/      # Domain submission types matching API contract
│   └── shared/
│       ├── components/  # Reusable UI primitives (Card)
│       └── types/       # Shared enums and coordinates
├── App.tsx              # Root application entry with stateful navigation
├── app.json             # Expo configuration manifest
├── package.json         # Dependencies and scripts
└── tsconfig.json        # Strict TypeScript configuration
```

## Quickstart

### 1. Install Dependencies

In PowerShell:
```powershell
cd mobile
npm install
```

### 2. Configure Backend URL

Set the backend endpoint in your environment or `.env`:
```powershell
# For Android Emulator:
$env:EXPO_PUBLIC_API_BASE_URL="http://10.0.2.2:8000/api/v1"

# For iOS Simulator / Web / Local:
$env:EXPO_PUBLIC_API_BASE_URL="http://localhost:8000/api/v1"
```

### 3. Verify TypeScript Strict Compilation

```powershell
npm run typecheck
```

### 4. Start Expo Development Server

```powershell
npm start
```
Press `w` to open web, or scan QR code with Expo Go on a mobile device.

## Implementation Status

- **IMPLEMENTED**:
  - Typed API client with request timeout and `X-Request-ID` propagation
  - Domain types aligned with backend `/api/v1/reports` JSON schema
  - `ReportCreateScreen` with form validation, location stub, and attached evidence
  - `ReportDetailScreen` with tracking ID display, status badge, and lifecycle timeline
  - Strict TypeScript configuration with zero type errors
- **PLANNED**:
  - Native camera preview and frame capture (Sprint 2)
  - Edge image preprocessing (resize, normalize, quality scoring) (Sprint 2/3)
  - Lightweight on-device visual inference (Sprint 3)
  - Offline report queue with SQLite persistence (Sprint 6)
