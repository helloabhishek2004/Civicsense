# CivicSense — Presentation Demo Script

**Duration:** 5–8 minutes
**Prerequisites:** Backend running on port 8000, dashboard running on port 5173, pilot dataset seeded

---

## Step 1: Introduction (30 seconds)

> "CivicSense is an AI-assisted civic issue reporting and aggregation platform. When citizens report problems like potholes, garbage, or water leakage, multiple reports often describe the same underlying issue. CivicSense uses text similarity and geospatial analysis to identify related reports, routes uncertain cases to human officers for review, and provides explainable priority scoring."

**Show:** Landing page or overview dashboard

---

## Step 2: Dashboard Overview (30 seconds)

1. Open `http://localhost:5173`
2. Log in with any email and role (prototype auth)
3. Show the Overview page with KPIs:
   - Total Reports
   - Pending Review
   - In Progress
   - Resolved Today

> "The dashboard provides real-time visibility into incoming reports, department workloads, and AI pipeline status."

**Show:** Overview page

---

## Step 3: Navigate to AI Operations (30 seconds)

1. Click **AI Operations** in the sidebar
2. Click the **Candidate Duplicate Reviews** tab
3. Point out the pending matches count badge

> "The AI Operations page has two tabs: the pipeline monitor and the candidate duplicate review queue. Six pending matches require officer review."

**Show:** AI Operations → Matches tab

---

## Step 4: Explain a Candidate Match (1 minute)

1. Point to the first pending match in the table
2. Explain the columns:
   - **Report**: The incoming citizen report
   - **Target Defect Cluster**: The existing issue it may match
   - **Match Confidence**: The combined similarity score (45%–70%)
   - **Signals Breakdown**: Text similarity, spatial distance, category match
   - **Engine Rationale**: Why the system flagged this as a candidate

> "This report describes a 'dangerous road condition near the school.' The system found it is 7.5 meters from an existing pothole issue, with 48% text similarity and matching category. The combined score of 64% falls in the candidate range, meaning it needs human review."

**Show:** Match table row with details

---

## Step 5: Approve a Match (1 minute)

1. Click **Approve** on the first match
2. Show the approval modal:
   - Incoming report ID
   - Target issue ID
   - Similarity score
   - Spatial proximity
   - Optional reviewer notes
3. Click **Confirm Linkage**
4. Show the match disappears from the pending queue

> "By approving this match, the officer confirms that this report represents the same pothole. The report is now linked to the issue, the issue's report count increases, and priority is automatically recomputed."

**Show:** Approval modal → confirmation → updated queue

---

## Step 6: Reject a Match (1 minute)

1. Click **Reject** on another match
2. Show the rejection modal:
   - Reviewer notes field
   - Optional: "Link to Alternate Issue" field
3. Add a note: "Different issue type - not a duplicate"
4. Click **Confirm Rejection**

> "By rejecting, the officer determines this is a different issue. The report remains independent or can be linked to an alternate issue if the officer identifies the correct cluster."

**Show:** Rejection modal → confirmation → updated queue

---

## Step 7: Show Audit Trail (30 seconds)

1. Navigate to the match detail or issue detail page
2. Show the approved/rejected status
3. Show reviewer identity, notes, and timestamps

> "Every decision is audit-logged. The system records who reviewed the match, what decision was made, when it was made, and any notes. This provides full traceability for municipal accountability."

**Show:** Audit trail / match detail

---

## Step 8: Show Priority and Issue Detail (30 seconds)

1. Navigate to **Issues** or click through from a match to the issue detail page
2. Show the priority breakdown:
   - Severity score
   - Report volume score
   - Unique reporter score
   - Recency score
   - Persistence score
   - Final priority level (CRITICAL / HIGH / MEDIUM / LOW)

> "Priority is computed from five weighted factors. Officers can see exactly why an issue received its priority level, making the scoring transparent and auditable."

**Show:** Issue detail with priority breakdown

---

## Step 9: Show Health and System Status (15 seconds)

1. Navigate to `http://localhost:8000/health` or show the health indicator
2. Point out:
   - Database status: healthy
   - MiniLM model: READY
   - Pending candidate matches count

> "The health endpoint provides real-time system status including database connectivity, model readiness, and pending review counts."

**Show:** Health endpoint response

---

## Step 10: Limitations and Future Scope (30 seconds)

> "Important context: This is a prototype system. Authentication is simulated (X-Reviewer-ID header accepts any value). Evaluation metrics are on synthetic data only, not real civic reports. The system uses text-only similarity — image classification has been piloted but not integrated. There is no real municipal deployment."

> "Future work includes production authentication, image-based classification, real-world evaluation, and multilingual support."

**Show:** Limitations slide or verbal summary

---

## Fallback: If Live Demo Fails

If the backend or dashboard is not running, use the API directly:

```bash
# Health check
curl http://localhost:8000/health

# List pending matches
curl -H "X-Reviewer-ID: demo-officer" http://localhost:8000/api/v1/matches/pending

# Approve a match
curl -X POST -H "Content-Type: application/json" -H "X-Reviewer-ID: demo-officer" \
  http://localhost:8000/api/v1/matches/{match_id}/approve \
  -d '{"reviewer_id": "demo-officer", "notes": "Confirmed duplicate"}'

# List issues
curl http://localhost:8000/api/v1/issues

# Priority breakdown
curl http://localhost:8000/api/v1/issues/{issue_id}/priority
```

---

## Key UI Labels (Verified)

- Sidebar: Overview, Reports Queue, AI Operations, Live Map, Analytics, Departments, Staff & Roles, Settings
- AI Operations tabs: "Pipeline Stages & Execution", "Candidate Duplicate Reviews"
- Match columns: Report, Target Defect Cluster, Match Confidence, Signals Breakdown, Engine Rationale, Review Actions
- Buttons: "Approve", "Reject", "Confirm Linkage", "Confirm Rejection", "Cancel"
- Status indicators: "Pipeline: Operational", "Auto-Sync ON/OFF"
- Reviewer notice: "Reviewer Identity Required", "Read-Only Permission"
