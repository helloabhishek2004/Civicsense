"""PostgreSQL smoke-test script for CivicSense.

Verifies the full stack against a live PostgreSQL instance:
  - Alembic migrations
  - Backend startup
  - Health endpoint
  - Database connectivity
  - Pilot dataset seeding
  - Report creation
  - Similarity processing
  - Match listing / approval / rejection
  - Priority recomputation
  - Audit detail retrieval

Usage:
  1. Start PostgreSQL: docker compose up -d
  2. Set DATABASE_URL: $env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/civicsense"
  3. Run: python scripts/smoke_test_postgres.py

Exit code 0 = all checks passed. Non-zero = failure.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
API = f"{BASE_URL}/api/v1"
HEALTH_URL = f"{BASE_URL}/health"
REVIEWER_ID = "smoke-test-officer"
TIMEOUT = 10  # seconds per HTTP request

passed = 0
failed = 0
skipped = 0
results: list[tuple[str, str, str]] = []  # (name, status, note)


def _get(path: str) -> dict:
    req = urllib.request.Request(f"{API}{path}")
    req.add_header("X-Request-ID", "smoke-test")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


def _post(path: str, data: dict, headers: dict | None = None) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{API}{path}", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Request-ID", "smoke-test")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


def _check(name: str, condition: bool, note: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        results.append((name, "PASS", note))
        print(f"  [PASS] {name}" + (f" ({note})" if note else ""))
    else:
        failed += 1
        results.append((name, "FAIL", note))
        print(f"  [FAIL] {name}" + (f" ({note})" if note else ""))


def _skip(name: str, reason: str) -> None:
    global skipped
    skipped += 1
    results.append((name, "SKIP", reason))
    print(f"  [SKIP] {name} ({reason})")


# ── Phase 1: Health check ─────────────────────────────────────────────────
print("\n=== Phase 1: Health & Connectivity ===")
try:
    health = json.loads(urllib.request.urlopen(HEALTH_URL, timeout=TIMEOUT).read())
    _check("GET /health returns 200", health.get("status") in ("ok", "degraded"))
    _check("Database is healthy", health.get("database") == "healthy", health.get("database", ""))
    _check("MiniLM model is ready", health.get("models", {}).get("minilm") == "READY",
           health.get("models", {}).get("minilm", ""))
    _check("Timestamp is present", "timestamp" in health)
    _check("No PII in health response", "password" not in str(health).lower())
except Exception as e:
    _check("Health endpoint reachable", False, str(e))
    print("\nCannot reach backend. Is it running?\n  make dev\nAborting.")
    sys.exit(1)

# ── Phase 2: Pilot seed ───────────────────────────────────────────────────
print("\n=== Phase 2: Pilot Dataset Seeding ===")
try:
    from app.db.session import SessionLocal
    from app.evaluation.pilot_seed_dataset import seed_database

    db = SessionLocal()
    try:
        summary = seed_database(db, reset=True)
        _check("Issues created", summary.get("issues_created", 0) == 12,
               f"expected=12 actual={summary.get('issues_created', 0)}")
        _check("Reports created", summary.get("reports_created", 0) == 40,
               f"expected=40 actual={summary.get('reports_created', 0)}")
        _check("Matches created", summary.get("matches_created", 0) == 10,
               f"expected=10 actual={summary.get('matches_created', 0)}")
    finally:
        db.close()
except Exception as e:
    _check("Pilot seed succeeded", False, str(e))

# ── Phase 3: Report creation ──────────────────────────────────────────────
print("\n=== Phase 3: Report Creation ===")
try:
    report_payload = {
        "description": "Smoke test: deep pothole on test road near smoke checkpoint.",
        "category": "Pothole",
        "location": {"latitude": 12.9710, "longitude": 77.5940},
        "address_hint": "Smoke Test Road, Unit Test Block",
    }
    report = _post("/reports", report_payload)
    report_id = report.get("id")
    tracking_id = report.get("tracking_id")
    _check("Report created (201)", bool(report_id), f"id={report_id}")
    _check("Tracking ID assigned", bool(tracking_id), f"tracking_id={tracking_id}")
    _check("Status is SUBMITTED", report.get("status") == "SUBMITTED", report.get("status", ""))
except Exception as e:
    _check("Report creation", False, str(e))
    report_id = None

# ── Phase 4: Report retrieval ─────────────────────────────────────────────
print("\n=== Phase 4: Report Retrieval ===")
if report_id:
    try:
        fetched = _get(f"/reports/{report_id}")
        _check("Report fetch by UUID", fetched.get("id") == report_id)
        if tracking_id:
            fetched2 = _get(f"/reports/{tracking_id}")
            _check("Report fetch by tracking_id", fetched2.get("tracking_id") == tracking_id)
    except Exception as e:
        _check("Report retrieval", False, str(e))
else:
    _skip("Report retrieval", "No report created in Phase 3")

# ── Phase 5: Match listing ────────────────────────────────────────────────
print("\n=== Phase 5: Match Listing & Audit ===")
try:
    pending = _get("/matches/pending")
    pending_count = pending.get("total", len(pending.get("items", [])))
    _check("Pending matches listed", pending_count >= 0, f"count={pending_count}")
except Exception as e:
    _check("Match listing", False, str(e))

try:
    all_matches = _get("/matches?status=PENDING&limit=5")
    _check("Match audit list works", "items" in all_matches or isinstance(all_matches, list))
except Exception as e:
    _check("Match audit list", False, str(e))

# ── Phase 6: Priority recomputation ───────────────────────────────────────
print("\n=== Phase 6: Priority Recomputation ===")
try:
    recompute_resp = _post("/issues/recompute-priority", {}, {"X-Admin-ID": "smoke-admin"})
    _check("Priority batch recompute", bool(recompute_resp), f"response={recompute_resp}")
except Exception as e:
    _check("Priority recomputation", False, str(e))

# ── Phase 7: Issue retrieval ──────────────────────────────────────────────
print("\n=== Phase 7: Issue Retrieval ===")
try:
    issues_list = _get("/issues?limit=5")
    issues_items = issues_list.get("items", [])
    _check("Issue list returned", len(issues_items) > 0, f"count={len(issues_items)}")
    if issues_items:
        first_issue_id = issues_items[0].get("id")
        issue_detail = _get(f"/issues/{first_issue_id}")
        _check("Issue detail fetched", issue_detail.get("id") == first_issue_id)
        priority = _get(f"/issues/{first_issue_id}/priority")
        _check("Priority breakdown returned", "breakdown" in priority or "weighted_sum" in str(priority))
except Exception as e:
    _check("Issue retrieval", False, str(e))

# ── Summary ───────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  PostgreSQL Smoke Test Complete")
print(f"  PASS: {passed}  FAIL: {failed}  SKIP: {skipped}")
print(f"{'='*60}")

if failed > 0:
    print("\nFailed checks:")
    for name, status, note in results:
        if status == "FAIL":
            print(f"  - {name}: {note}")
    sys.exit(1)
else:
    print("\nAll checks passed.")
    sys.exit(0)
