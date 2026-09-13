# CivicSense API Reference

**Base URL:** `http://localhost:8000/api/v1`
**OpenAPI Docs:** `http://localhost:8000/docs`
**ReDoc:** `http://localhost:8000/redoc`

---

## Authentication (Prototype)

All match review endpoints require the `X-Reviewer-ID` header.

```
X-Reviewer-ID: officer-badge-number
```

> **WARNING:** This is prototype-only authentication. It accepts any non-empty string.
> Production requires JWT/session validation and RBAC.

---

## Standard Headers

| Header | Direction | Description |
|---|---|---|
| `X-Request-ID` | Both | UUID for request tracing |
| `X-Reviewer-ID` | Request | Reviewer identity (match review) |

---

## Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid report payload",
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "details": []
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Invalid request payload |
| `ENTITY_NOT_FOUND` | 404 | Resource does not exist |
| `REVIEWER_AUTH_REQUIRED` | 401 | Missing X-Reviewer-ID header |
| `REVIEWER_MISMATCH` | 403 | Header doesn't match payload |
| `MATCH_ALREADY_REVIEWED` | 409 | Match is not in PENDING state |

---

## Endpoints

### Health

#### `GET /health`
Basic liveness check.

**Response:**
```json
{
  "status": "ok",
  "service": "civicsense-api",
  "version": "0.1.0",
  "timestamp": "2026-09-13T12:00:00Z",
  "database": "healthy",
  "models": {
    "minilm": "READY",
    "degraded_mode": false
  },
  "pending_candidate_matches": 6
}
```

---

### Reports

#### `POST /api/v1/reports`
Submit a new citizen report.

**Request:**
```json
{
  "description": "Deep pothole near school gate on MG Road",
  "category": "Pothole",
  "location": {
    "latitude": 12.9716,
    "longitude": 77.5946
  },
  "address_hint": "Near Bishop Cotton School, MG Road",
  "citizen_name": "Demo Citizen",
  "citizen_phone": "+91-9876500001",
  "edge_metadata": {
    "client_version": "1.0.0",
    "image_quality_score": 0.85
  }
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "tracking_id": "REP-202609-000001",
  "status": "SUBMITTED",
  "category": "Pothole",
  "created_at": "2026-09-13T12:00:00Z"
}
```

#### `GET /api/v1/reports`
Paginated list of reports.

**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page |
| `citizen_id` | string | — | Filter by citizen |
| `issue_id` | string | — | Filter by linked issue |
| `status` | string | — | Filter by status |
| `category` | string | — | Filter by category |

#### `GET /api/v1/reports/stats`
Aggregated intake metrics.

**Response:**
```json
{
  "totalReports": 40,
  "pendingReview": 6,
  "inProgress": 12,
  "resolvedToday": 2,
  "criticalIssues": 3,
  "avgResolutionDays": 4.2,
  "aiAgreementRate": 0.78
}
```

#### `GET /api/v1/reports/{id}`
Retrieve single report by UUID or tracking ID.

#### `PATCH /api/v1/reports/{identifier}/transition`
Advance report lifecycle status.

**Request:**
```json
{
  "target_status": "ASSIGNED",
  "reason": "Manual triage assignment",
  "actor": "triage-officer-42"
}
```

---

### Issues

#### `GET /api/v1/issues`
Paginated issue list sorted by priority.

**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page |
| `sort_by` | string | `priority` | Sort: priority, created, updated, report_count |
| `category` | string | — | Filter by category |
| `status` | string | — | Filter by status |

#### `GET /api/v1/issues/{id}`
Single issue detail with report count and priority level.

#### `GET /api/v1/issues/{id}/priority`
Priority breakdown with component scores.

**Response:**
```json
{
  "issue_id": "uuid",
  "priority_score": 72.5,
  "priority_level": "CRITICAL",
  "breakdown": {
    "severity_score": 0.85,
    "report_volume_score": 0.92,
    "unique_reporter_score": 0.78,
    "recency_score": 0.65,
    "persistence_score": 0.30,
    "weighted_sum": 0.725,
    "final_score_0_100": 72.5
  },
  "computed_at": "2026-09-13T12:00:00Z"
}
```

#### `POST /api/v1/issues/recompute-priority`
Batch recompute all issue priorities (admin-only).

**Headers:** `X-Admin-ID: admin-id`

---

### Matches

#### `GET /api/v1/matches/pending`
List all PENDING candidate matches.

**Headers:** `X-Reviewer-ID: required`

#### `GET /api/v1/matches`
Audit list with filtering.

**Query Parameters:**
| Param | Type | Description |
|---|---|---|
| `status` | string | PENDING, APPROVED, REJECTED, SUPERSEDED |
| `report_id` | string | Filter by report UUID |
| `issue_id` | string | Filter by issue UUID |
| `limit` | int | Page size (default 20) |

#### `GET /api/v1/matches/{match_id}`
Match detail with full reasoning chain.

#### `POST /api/v1/matches/{match_id}/approve`
Approve a candidate match (link report to issue).

**Headers:** `X-Reviewer-ID: required`

**Request:**
```json
{
  "reviewer_id": "officer-badge-42",
  "notes": "Confirmed duplicate: same pothole, same location"
}
```

**Response:** Updated match with status `APPROVED`.

#### `POST /api/v1/matches/{match_id}/reject`
Reject a candidate match.

**Request:**
```json
{
  "reviewer_id": "officer-badge-42",
  "notes": "Distinct issue: different defect class",
  "link_to_issue_id": "alternate-issue-uuid"
}
```

**Response:** Updated match with status `REJECTED`.

---

### Departments

#### `GET /api/v1/departments`
List active departments with workload metrics.

#### `GET /api/v1/departments/{id}`
Department detail by UUID or code (e.g., `ROADS`).

#### `GET /api/v1/departments/{id}/stats`
Workload stats (assigned, in-progress, resolved, rejected).

#### `GET /api/v1/departments/{id}/reports`
Paginated reports assigned to department.

---

### Report Lifecycle Actions

#### `POST /api/v1/reports/{id}/assign`
Assign report to department.

#### `POST /api/v1/reports/{id}/acknowledge`
Department acknowledges job.

#### `POST /api/v1/reports/{id}/complete`
Record field remediation.

#### `POST /api/v1/reports/{id}/department-reject`
Department declines with structured reason.

---

## Pagination

All list endpoints support cursor-based pagination:

```json
{
  "items": [...],
  "total": 40,
  "page": 1,
  "page_size": 20,
  "pages": 2
}
```
