# CivicSense — Controlled Pilot Demo Runbook

**Version:** 1.0.0
**Last Updated:** 2026-09-13
**Status:** READY FOR INTERNAL DEMO

---

## Preconditions

- Python 3.12+
- Node.js 18+
- Docker Desktop (for PostgreSQL 16)
- MiniLM model at `models/all_minilm_l6_v2/` (pre-downloaded)

## 1. Startup Commands

```powershell
# 1. Start PostgreSQL
docker compose up -d

# 2. Set environment
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/civicsense"
Copy-Item .env.example .env

# 3. Apply migrations
cd backend
python -m alembic upgrade head

# 4. Seed pilot dataset
python scripts/seed_pilot_dataset.py --seed-db --reset

# 5. Start backend (new terminal)
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Start dashboard (new terminal)
cd dashboard
npm install
npm run dev
```

## 2. Environment Variables

| Variable | Value | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/civicsense` | PostgreSQL 16 |
| `API_ENV` | `development` | |
| `VITE_DATA_MODE` | `api` | Use `mock` for offline demo |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | |
| `VITE_GOOGLE_MAPS_API_KEY` | (your key) | For map features |

## 3. Seed Commands

```powershell
# Export dataset to JSON (no DB)
python scripts/seed_pilot_dataset.py --export-only

# Seed database (safe, idempotent with skip)
python scripts/seed_pilot_dataset.py --seed-db

# Reset and re-seed (destructive, requires --reset)
python scripts/seed_pilot_dataset.py --seed-db --reset
```

**Expected seed output:**
- 40 reports created
- 12 issues created
- 10 matches created (6 PENDING, 4 REJECTED)

## 4. Login / Reviewer Instructions

1. Open `http://localhost:5173`
2. Log in with any officer credentials (prototype auth):
   - Badge Number: `TRIAGE-001`
   - Role: `triage_officer`
3. Navigate to **AI Operations** → **Candidate Duplicate Reviews** tab

## 5. Demo Scenario Navigation

### Scenario A — New Issue (Standalone Report)
- **Navigate to:** `/reports/REP-202609-STANDALONE01`
- **Expected:** Report shows no linked issue; creates independent issue upon AI processing

### Scenario B — Candidate Match (Pending Review)
- **Navigate to:** AI Operations → Matches tab
- **Expected:** 6 pending candidate matches displayed
- **Key records:** `REP-202609-CAND01` through `REP-202609-CAND06`

### Scenario C — Approve Match
1. In Matches tab, click **Approve** on any pending match
2. Review the similarity evidence (text, distance, category)
3. Click **Confirm Linkage**
4. **Expected:** Match disappears from pending queue; report linked to issue; priority recomputed

### Scenario D — Reject Match
1. In Matches tab, click **Reject** on any pending match
2. Add rejection notes (optional)
3. Click **Confirm Rejection**
4. **Expected:** Match status becomes REJECTED; report remains independent

### Scenario E — Reject and Link to Alternate Issue
1. Click **Reject** on a pending match
2. In the "Link to Alternate Issue" field, enter a valid issue UUID
3. Click **Confirm Rejection**
4. **Expected:** Original candidate rejected; report linked to alternate issue

### Scenario F — Repeat Review Protection
1. Attempt to approve/reject an already-approved or rejected match
2. **Expected:** API returns 409 `MATCH_ALREADY_REVIEWED`
3. **UI:** Clear, non-destructive error message displayed

## 6. Verification Checklist

| Check | Expected | API |
|---|---|---|
| Health endpoint | `status: ok` | `GET /health` |
| Pending matches count | ≥ 0 | `GET /api/v1/matches/pending` |
| Match approve | 200 + APPROVED status | `POST /api/v1/matches/{id}/approve` |
| Match reject | 200 + REJECTED status | `POST /api/v1/matches/{id}/reject` |
| Repeat review | 409 MATCH_ALREADY_REVIEWED | Same endpoint, second call |
| Priority breakdown | Component scores | `GET /api/v1/issues/{id}/priority` |
| Issue list | Sorted by priority | `GET /api/v1/issues` |
| Report detail | Shows linked issue | `GET /api/v1/reports/{id}` |

## 7. Reset Instructions

```powershell
# Reset database and re-seed
python scripts/seed_pilot_dataset.py --seed-db --reset
```

## 8. Troubleshooting

| Problem | Solution |
|---|---|
| `DATABASE_URL` not set | Set `$env:DATABASE_URL` before starting backend |
| MiniLM model not found | Run once with model in `models/all_minilm_l6_v2/` |
| Port 8000 in use | Kill existing uvicorn process |
| Dashboard shows no data | Ensure `VITE_DATA_MODE=api` in `dashboard/.env` |
| 401 on match review | Ensure logged in with valid badge number |
| 409 on match review | Match already reviewed (expected behavior) |

## 9. Known Limitations

- Prototype authentication only (X-Reviewer-ID header)
- No production-grade RBAC
- Synthetic-only evaluation metrics
- GPS jitter and 50m spatial cutoff
- Severity is keyword-heuristic, not ML-classified
- No image AI (text-only analysis currently)
- MiniLM model required at startup
