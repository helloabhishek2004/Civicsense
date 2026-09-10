# CivicSense API Documentation

## Overview

The CivicSense API is built using **FastAPI** with structured JSON request/response validation via Pydantic v2.

## Base URLs

- Development API Root: `http://localhost:8000`
- Version 1 API Prefix: `http://localhost:8000/api/v1`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- ReDoc Docs: `http://localhost:8000/redoc`

## Standard Headers

- `X-Request-ID`: Client or server-generated UUID tracking the lifecycle of each request across logs and error traces.

## Standard Error Response Format

All 4xx and 5xx responses conform to a unified error structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid report payload",
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "details": [
      {
        "field": "location.latitude",
        "issue": "Input should be greater than or equal to -90"
      }
    ]
  }
}
```

## Implemented Endpoints (Phase 0 Bootstrap)

### 1. Health Checks
- `GET /health`: Basic liveness check.
- `GET /api/v1/health`: Detailed API v1 service health.

Response:
```json
{
  "status": "ok",
  "service": "civicsense-api",
  "version": "0.1.0"
}
```

### 2. Reports
- `POST /api/v1/reports`: Submit a new citizen report.
  - Automatically initializes report in `SUBMITTED` state.
  - Assigns unique database UUID and human-readable `tracking_id` (e.g. `REP-202609-00001`).
  - Persists attached evidence references.
- `GET /api/v1/reports`: List recent reports with pagination.
- `GET /api/v1/reports/{id}`: Retrieve a specific report by UUID or tracking ID.
