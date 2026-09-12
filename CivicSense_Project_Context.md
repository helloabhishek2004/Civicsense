# CivicSense — Project Context & Engineering Specification

> **Purpose of this document:** This is the canonical project-context document for AI coding agents, developers, designers, and contributors. It defines what CivicSense is, why it exists, its architecture, data flow, AI/ML responsibilities, engineering constraints, scope, and intended implementation direction. Any AI agent picking up work on this project should read this file first.

---

## 1. Project Identity

**Name:** CivicSense
**Tagline:** From Citizen Reports to Civic Intelligence
**Type:** Hybrid edge-cloud, multimodal AI-assisted civic issue reporting and decision-support platform.

**Academic domains integrated:**
1. Artificial Intelligence Systems Engineering
2. Machine Vision and Pattern Recognition
3. Data Mining and Text Analytics

These are not three unrelated modules bolted together — they operate as connected components of one real software system.

**Team:** Abhishek, Anagha, Sree Nivetha

---

## 2. Core Idea

A citizen reports a civic problem using:

- A photograph
- A natural-language description
- Live GPS coordinates
- Timestamp
- Optional structured info

> Example: "Large pothole near the school entrance. Water collects here after rain and two bikes have already fallen."

The mobile app performs **privacy-conscious preprocessing and lightweight AI locally**. The processed representation goes to the server, where stronger models combine:

- Visual evidence
- Textual evidence
- Location
- Historical reports
- Similarity information
- Severity indicators
- Public-impact signals

Output produced:

- Issue category
- Confidence
- Severity
- Priority
- Evidence agreement/conflict
- Duplicate/similarity info
- Human-review requirement

Verified reports become structured historical data. Data Mining then discovers civic hotspots, recurring issues, temporal trends, frequent issue combinations, clusters, and correlations — surfaced on an authority-facing dashboard.

**Core philosophy:** *AI handles scale, humans handle judgment, historical data reveals the bigger picture.*

---

## 3. Central Design Principle — The Lifecycle

```
EDGE → understand submission locally
  ↓
SERVER AI → deeper multimodal reasoning
  ↓
DECISION ENGINE → categorize, assess, rank, route
  ↓
HUMAN → verify uncertain/important cases
  ↓
CIVIC DATA → store verified events + outcomes
  ↓
DATA MINING → find patterns across many reports
  ↓
AUTHORITY → prioritize + manage action
  ↓
FEEDBACK → capture verification + resolution
  ↓
MLOps → evaluate + improve models
```

---

## 4. Problem Statement

Traditional civic complaint systems behave like digital forms:

```
Citizen → Submit → Store → Human reads → Human decides → Human prioritizes
```

At scale this causes: manual image inspection, manual categorization, inconsistent severity assessment, slow prioritization, duplicate complaints, unstructured text overload, underused historical data, and no clear signal for what needs attention first.

CivicSense adds an intelligent processing and analytics layer on top of this flow.

---

## 5. What CivicSense Is NOT

- A simple pothole detector
- A generic image-classification app
- A basic complaint form
- A chatbot for civic complaints
- A fully autonomous government system
- A system that auto-orders physical repairs
- A replacement for human authorities
- A giant city-wide AI platform with dozens of unrelated models

CivicSense **is** an AI-assisted civic decision-support and intelligence platform.

---

## 6. Primary Goals

- Multimodal citizen report submission
- Local (edge) image preprocessing where feasible
- Lightweight on-device visual inference
- Local text preprocessing where practical
- Preserve access to original evidence
- Send compact AI representations + metadata to server
- Strong server-side AI inference
- Combine image + text evidence
- Detect agreement/disagreement between modalities
- Classify issues, estimate confidence and severity separately
- Calculate priority score
- Detect duplicate/related reports
- Route uncertain/high-impact cases to humans
- Maintain full report lifecycle
- Mine historical data for patterns
- Produce geospatial + temporal insights
- Capture human corrections as feedback
- Support model evaluation and retraining

---

## 7. Non-Goals for the Initial Version

Do **not** let scope explode. The initial system should not require:

- Dozens of civic categories
- City-wide production deployment
- Autonomous physical intervention
- Real-time traffic/police/ambulance integration
- Full weather intelligence
- A massive LLM-based reasoning system or custom foundation model
- Proprietary cloud infra / expensive GPU hardware
- Perfect prediction or fully autonomous decisions

These are future extensions, not MVP requirements.

---

## 8. Recommended Initial Civic Categories

1. Pothole
2. Road Crack / Surface Damage
3. Water Accumulation / Drainage Issue
4. Garbage / Waste Accumulation
5. Damaged Civic Infrastructure

Final category set depends on dataset availability and model performance. Architecture must allow new categories later without a rewrite.

---

## 9. End-to-End User Flow

```
Open App → Create Report → Capture/Select Image → Enter Description
  → GPS Auto-Attached → Local Validation → On-Device Preprocessing
  → Optional Local Prediction → Compact Payload → Submit
  → Server Processing → AI Result → Status/Tracking
```

---

## 10. Example Report Walkthrough

**Citizen input:**
- Image: large pothole filled with water
- Text: "Large pothole near the college entrance. Water collects here after rain and bikes are having difficulty passing."
- Location: GPS coords · Timestamp: 2026-XX-XX

**Mobile output:**
- Local category: Pothole · Local confidence: 0.91
- Image quality: 0.87 · Image embedding: [...] · Text representation: [...]
- Model version: `vision-mobile-v1`

**Server output:**
- Vision: Pothole = 0.95 · Text: Pothole = 0.93 (safety concern detected)
- Historical: 7 related reports · Context: near school

**Fusion:** Issue = Pothole, Secondary = Water accumulation, Evidence = strong agreement

**Decision:** Confidence = High, Severity = High, Priority = Critical, Human verification = Required (critical severity)

**Human:** Reviewer confirms → **DB:** Issue Group "Pothole at Location X", 8 reports, Status = Verified → **Authority:** Priority Critical, Status Assigned → **Later:** Resolved → Resolution verified → historical data updated.

**Data Mining later reveals:** Location X is a repeated road-damage hotspot; Pothole + water is a frequent pattern; rainy periods correlate with higher drainage/road reports.

---

## 11. Mobile / Edge Layer

**Purpose:** reduce unnecessary data transfer and server workload while performing useful preliminary understanding — *not* run the entire AI pipeline.

**Mobile responsibilities:**
- Image: capture, validation, resize, normalization, quality estimation, lightweight inference, embedding/feature extraction
- Text: cleaning, tokenization/normalization, optional lightweight representation
- Metadata: GPS, timestamp, payload construction, secure transmission, offline queueing

### Mobile Image Pipeline
```
Camera → Raw Image → Quality Check → Resize → Normalization
  → Lightweight Vision Model → Feature Extraction/Embedding
  → Local Prediction → Compact Representation
```
Possible outputs: image embedding, local category probabilities, image quality score, model version, optional detection metadata. Model/embedding architecture must be chosen via benchmarking.

### Mobile Text Pipeline
```
Raw Text → Cleaning → Normalization → Tokenization
  → Optional Stop-word Handling → Optional Stemming/Lemmatization → Representation
```
Options for what's sent to server:
- **A:** Cleaned text + server-generated embedding
- **B:** Cleaned text + lightweight local embedding
- **C:** Local embedding + minimal metadata

Choice driven by accuracy, device latency, privacy, payload size, model availability, implementation complexity. **Don't vectorize on-device just because it sounds more advanced.**

---

## 12. Critical Evidence-Preservation Rule

Never permanently discard original evidence just because an embedding was generated. An embedding is a *representation*, not the original image.

```
Primary AI payload → Embeddings + metadata
Evidence layer      → Controlled original-image access
```

If human verification is needed, the original image must remain retrievable via a secure mechanism (encrypted object storage, temporary evidence storage, secure image reference, or controlled server-side evidence store).

**Why not send only raw images?** Higher bandwidth, more server preprocessing, more repeated work, higher latency.

**Why not send only embeddings?** Original evidence unavailable, future models may be incompatible with old embeddings, no reprocessing of historical images, harder debugging, reproducibility suffers.

**→ Recommended architecture: representation-first, evidence-preserving.**

---

## 13. Model Versioning Requirement

Every locally generated representation must carry its model/preprocessing version:

```json
{
  "vision_model": "civicsense-mobile-vision-v1",
  "vision_embedding_version": "v1",
  "text_pipeline_version": "v1"
}
```

Essential because future models may produce incompatible representations.

---

## 14. Server Architecture

```
API Gateway → Validation → Report Ingestion → AI Processing
  → Multimodal Fusion → Similarity Search → Decision Engine
  → Human Review Routing → Database
```

**Server AI layer:** Vision Model, Text Model, Multimodal Fusion Model, Similarity Search, Duplicate Detection, Decision Engine.

The server must **not** blindly trust the mobile prediction — mobile output is evidence, not final truth.

---

## 15. Machine Vision Component

**Purpose:** answer "what is visible in the submitted image?"

**Potential tasks:** civic object detection, image classification, segmentation, feature extraction, similarity comparison, image quality assessment.

**Syllabus-aligned techniques (use where they solve a real problem, not all mandatory in production):**

- *Image processing:* average/median filtering, sharpening, unsharp masking, edge detection, Fourier/frequency-domain processing
- *Segmentation:* thresholding, dilation, erosion, connected component analysis, region-based segmentation, watershed
- *Feature extraction:* texture descriptors (LBP, GLCM), edge density/direction, color features, shape features
- *Feature matching:* SIFT/SURF (where legally/technically appropriate), image distance measures
- *Detection:* object detection/classification via YOLO-family or another lightweight detector

### Vision Model Strategy
```
Public Dataset → Preprocessing → Training/Fine-tuning → Evaluation
  → Model Optimization → Server Model → Mobile Optimization
```
Benchmark on: accuracy, precision, recall, F1, mAP (where applicable), model size, mobile inference latency, memory usage.

---

## 16. Text Analytics Component

**Purpose:** answer "what is the citizen reporting, and what contextual information is present?"

> Example: "Large pothole near school. Two bikes have fallen. Water collects after rain."
> Extracted: Issue = Pothole · Context = near school · Safety indicator = accidents/falls · Environmental factor = water accumulation · Severity indicator = large · Potential impact = high

### Text Processing Pipeline
```
Raw Complaint → Cleaning → Normalization → Tokenization
  → Stop-word Handling → Stemming/Lemmatization
  → Document Representation → Classification/Information Extraction
```

### Text Representation options
Bag of Words, N-Grams, TF-IDF, Word2Vec, GloVe, lightweight sentence embeddings.

A classical baseline — **TF-IDF + classifier** — is valuable: it gives a measurable baseline against more advanced representations. Compare methods where academically useful.

---

## 17. Multimodal Fusion

One of CivicSense's core features. Combines image + text + location + historical context into a multimodal decision.

**Agreement example:** Vision Pothole=0.94, Text Pothole=0.91 → strong agreement.

**Conflict examples:**
- Vision "Road crack"=0.91 vs Text "Pothole"=0.89 → evidence conflict → human verification
- Poor image quality + Vision confidence=0.42 + Text confidence=0.93 → insufficient visual evidence → human verification

### Fusion Strategies
- **Strategy A — Feature Fusion:** image embedding + text embedding + metadata → fusion → classifier/decision model. Likely the simplest strong research implementation.
- **Strategy B — Shared Multimodal Embedding:** image and text mapped into a shared space, enabling cross-modal semantic similarity.

Final strategy chosen based on model availability and experimental results.

---

## 18. Confidence vs Severity vs Priority

Three separate concepts — **never conflate them.**

- **Confidence:** how certain is the model about its prediction?
- **Severity:** how serious is the actual problem? (considers visual extent, issue type, safety-related text, public location, reported incidents, historical recurrence, evidence agreement)
- **Priority:** how urgently should this receive attention? (severity + public impact + report frequency + historical recurrence + location context + safety indicators + evidence confidence)

**Example:**
```
REPORT A: Pothole, Confidence 95%, Severity High, 17 reports at location,
          near school, previous incidents → Priority: CRITICAL

REPORT B: Road crack, Confidence 98%, Severity Low, 1 report,
          low public impact → Priority: LOW
```

The exact scoring model must be defined and experimentally evaluated — **do not present arbitrary weights as scientifically established.**

---

## 19. Similarity and Duplicate Detection

Identify potentially related reports by comparing image similarity + text similarity + geographic proximity + time proximity.

```
30 reports → Similarity analysis → same location/same issue
  → 1 civic issue + 30 supporting reports
```

Number of independent reports can itself become a priority signal.

**Issue vs Report distinction (essential):**
- **Report** = a citizen submission
- **Issue** = the potentially real-world civic problem
- Multiple reports can map to one issue group.

---

## 20. Human-in-the-Loop

CivicSense does not eliminate humans — it knows when to ask for judgment.

**Triggers for human review:** low confidence, image-text conflict, poor image quality, high severity, potentially critical issue, suspicious/duplicate behavior, out-of-distribution input, other defined uncertainty conditions.

**Reviewer sees:** original evidence, AI prediction, confidence, severity, priority, citizen description, location, related reports.

**Reviewer actions:** confirm, correct category, adjust severity, reject, mark duplicate, request additional evidence.

### Human Feedback Loop
```
AI Prediction → Human Review → Correction → Verified Label
  → Training/Evaluation Dataset → Future Model Improvement
```
This is the direct link into MLOps.

---

## 21. Report Lifecycle

CivicSense implements an explicit 11-state server-authoritative report lifecycle:

```
SUBMITTED → AI_PROCESSING → AI_PROCESSED → VERIFICATION_REQUIRED
  → VERIFIED → PRIORITIZED → ASSIGNED → IN_PROGRESS → RESOLVED
  → RESOLUTION_VERIFIED → CLOSED
```

### The Municipal Department Execution Workflow
Once an issue is verified by human review and prioritized, operational resolution shifts to municipal departments:
1. **Assignment (`PRIORITIZED` → `ASSIGNED`)**: The central triage officer assigns the report to a responsible municipal department (e.g. Roads & Bridges, Water Supply & Sewerage). The assignment record is immutably logged with `AssignmentStatus.ASSIGNED`.
2. **Acknowledgment (`ASSIGNED` → `IN_PROGRESS`)**: The department acknowledges the job order and assigns it to an operational field officer/crew. The report advances to `IN_PROGRESS`.
3. **Completion (`IN_PROGRESS` → `RESOLVED`)**: Upon fixing the defect on the ground, the department officer submits a completion report with mandatory field remediation notes (`resolver_notes` $\ge$ 5 characters). The assignment is marked `COMPLETED` and the report transitions to `RESOLVED`.
4. **Resolution Verification (`RESOLVED` → `RESOLUTION_VERIFIED`)**: A municipal inspector or triage officer inspects and verifies the resolution quality.
5. **Closure (`RESOLUTION_VERIFIED` → `CLOSED`)**: The report is formally closed. `CLOSED` is an immutable terminal state.

### The Department Rejection & Reassignment Loop
A critical operational reality is that departments may decline a dispatched ticket if it falls outside their purview or cannot be executed as dispatched:
- **Non-Destructive Rejection**: If a department declines an assigned job (due to `OUT_OF_JURISDICTION`, `INSUFFICIENT_ACCESS`, `DUPLICATE_WORK_ORDER`, `REQUIRES_MAJOR_BUDGET`, `INSUFFICIENT_INFORMATION`, or `OTHER`), the report is **NEVER closed, dismissed, or deleted**.
- **State Reversion**: The report transitions backwards from `ASSIGNED` back to `PRIORITIZED`.
- **Reassignment Flag**: The report is marked with `reassignment_required = True`.
- **Historical Context Preservation**: The previous department reference is preserved for triage transparency.
- **Audit Logging**: The active `ReportAssignment` record is updated to `AssignmentStatus.REJECTED` with the structured rejection reason, officer notes, and timestamp.
- **Triage Action**: The triage dashboard highlights the report with an urgent alert banner, allowing triage officers to reassign the report to the correct department with full historical context.

**Resolution tracking example:**
```
Issue: Pothole
Reported: 10:30 → Verified: 11:02 → Prioritized: 11:15 → Assigned (Roads): 12:15
Acknowledged (In Progress): 13:00 → Resolved (Asphalt patched): 16:30
Resolution verified: Next day 09:00 → Closed: Next day 09:15
```
Retain the issue and its resolution history — never delete the issue record after repair.

---

## 22. Data Mining Component

Operates primarily on **accumulated** verified reports, not single submissions. After thousands of reports exist, CivicSense asks: *what is happening across the civic environment?*

- **Hotspots:** `GPS Reports → Spatial Analysis/Clustering → Civic Hotspots` (e.g. Area A: 184 road-damage reports; Area C: 211 drainage reports)
- **Temporal Trends:** track how problem counts change month over month; look for seasonal/recurring patterns
- **Frequent Patterns:** discover issue combinations (e.g. `{Pothole, Water}`, `{Garbage, Odour}`) — "Pothole + water accumulation is a frequent combination"
- **Clustering:** group locations/reports by characteristics (low-density, road-damage-dominant, drainage-dominant, mixed high-problem)
- **Correlation:** e.g. Rainfall → Water accumulation → Road deterioration → Pothole reports. **Must be described as correlation unless causal evidence exists.**
- **Recurrence:** repeatedly-reported problems at the same location over multiple months → signals a recurring unresolved issue, feeds into priority

**Geospatial intelligence** should support: map visualization, spatial clustering, hotspot detection, proximity search, duplicate grouping, location-based prioritization, recurrence analysis.

---

## 23. Authority Dashboard

**Priority Queue example:**
```
CRITICAL — #10482 Pothole, 17 related reports, near school
HIGH     — #10392 Drainage, 8 reports
MEDIUM   — #10271 Road crack, 3 reports
```

**Map:** report locations, categories, severity, priority, hotspots, resolved/unresolved status.

**Analytics:** reports over time, category distribution, severity distribution, resolution time, recurring problems, hotspots, frequent patterns.

---

## 23b. Municipal Department Operations Subsystem & System-Wide Influence

Central triage officers and AI models do not fix potholes, repair blown streetlights, or clear blocked sewers—operational municipal divisions do. The Municipal Department Operations Subsystem is the operational bridge between administrative triage and physical ground resolution.

### 1. The `Department` Class & Model
`Department` serves as the canonical registry of real-world municipal operational divisions responsible for resolving civic defects:

- **Entity Schema**:
  - `id`: UUID (Primary Key)
  - `name`: VARCHAR(64), unique, indexed (e.g., `"Roads & Bridges"`, `"Solid Waste Management"`)
  - `code`: VARCHAR(32), unique, indexed short identifier (e.g., `"ROADS"`, `"WASTE"`, `"WATER"`, `"ELECTRICAL"`, `"PLANNING"`, `"PUBLIC_WORKS"`)
  - `description`: TEXT detailing jurisdictional scope and defect responsibilities
  - `head_name`: VARCHAR(128) operational lead/engineer title
  - `contact_email` & `contact_phone`: Official communication coordinates
  - `sla_hours_default`: Integer default Service Level Agreement window (hours)
  - `is_active`: Boolean operational availability flag
  - `created_at` & `updated_at`: Timezone-aware audit timestamps
- **Relational Integrity**:
  - `reports`: One-to-many relationship with `Report` (`Report.department_id` foreign key)
  - `assignments`: One-to-many relationship with `ReportAssignment` (`ReportAssignment.department_id` foreign key)
- **Canonical Default Divisions**:
  1. `ROADS` (Roads & Bridges): Road networks, potholes, asphalt paving, flyovers, footpaths, storm drains (48h SLA).
  2. `WASTE` (Solid Waste Management): Garbage clearance, municipal dumpsters, street sweeping, illegal dumping remediation (24h SLA).
  3. `WATER` (Water Supply & Sewerage): Potable water mains, leaks, manhole overflows, sewage blockages (36h SLA).
  4. `ELECTRICAL` (Street Lighting & Electrical): Streetlight fixtures, high-mast lamps, exposed electrical cables, feeder pillars (24h SLA).
  5. `PLANNING` (Town Planning & Enforcement): Public right-of-way encroachments, unauthorized construction, zoning violations (72h SLA).
  6. `PUBLIC_WORKS` (Public Works & Infrastructure): Municipal buildings, parks, structural maintenance, general civil works (72h SLA).

### 2. The `ReportAssignment` Class & Audit Ledger
`ReportAssignment` is an immutable historical audit entity recording each dispatch attempt:

- **Entity Schema**:
  - `id`: UUID (Primary Key)
  - `report_id`: UUID, Foreign Key to `reports.id` (ON DELETE CASCADE, indexed)
  - `department_id`: UUID, Foreign Key to `departments.id` (ON DELETE SET NULL, indexed)
  - `department_name`: VARCHAR(64), snapshot of department name at dispatch
  - `assigned_by`: VARCHAR(128), triage officer or system actor initiating dispatch
  - `assigned_to_officer`: VARCHAR(128), field officer/crew assigned within department
  - `status`: `AssignmentStatus` enum (`ASSIGNED`, `IN_PROGRESS`, `COMPLETED`, `REJECTED`)
  - `rejection_reason`: Structured `DepartmentRejectionReason` enum:
    - `OUT_OF_JURISDICTION`: Physical defect falls under a different municipal division
    - `INSUFFICIENT_ACCESS`: Site is inaccessible (e.g., locked private gate, flooded road)
    - `DUPLICATE_WORK_ORDER`: Another active ticket already addresses this physical defect
    - `REQUIRES_MAJOR_BUDGET`: Exceeds routine maintenance; requires capital budget approval
    - `INSUFFICIENT_INFORMATION`: Photos/coordinates insufficient to locate defect
    - `OTHER`: Exceptional operational circumstances (detailed in notes)
  - `notes`: TEXT containing dispatch instructions, remediation notes, or rejection explanations
  - `created_at` & `resolved_at`: Dispatch and completion/rejection timestamps

### 3. Domain Functionalities (`DepartmentService`)
The service layer exposes the operational capabilities required for municipal workflows:

- `list_departments(db, active_only)`: Directory listing of all divisions with calculated real-time workload statistics.
- `get_department(db, identifier)`: Resilient multi-identifier lookup by UUID, uppercase short code (`ROADS`), or name.
- `get_workload_stats(db, identifier)`: Real-time query calculating operational workload metrics:
  - `total_assigned`: Cumulative reports linked to the division.
  - `pending_acknowledgment`: Reports in `ASSIGNED` status awaiting departmental pickup.
  - `in_progress`: Reports actively being repaired by field crews.
  - `resolved`: Remediated reports awaiting inspector verification or closed.
  - `rejected_assignments`: Historical count of tickets declined by this department.
  - `reassignment_required`: Reports where previous assignment was rejected and reassignment is pending.
- `get_department_reports(db, identifier, status, priority, skip, limit)`: Paginated job queue with status/priority filtering.
- `assign_report(db, report_id, department_id, assigned_by, ...)`: Enforces `PRIORITIZED` → `ASSIGNED` lifecycle transition, creates `ReportAssignment` ledger entry, updates `Report.department_id`, and resets `reassignment_required = False`.
- `acknowledge_report(db, report_id, assigned_to_officer, notes)`: Transitions `AssignmentStatus` and `ReportStatus` from `ASSIGNED` to `IN_PROGRESS`.
- `complete_report(db, report_id, resolver_notes, resolved_by)`: Enforces $\ge 5$ char remediation notes, marks assignment `COMPLETED`, sets `resolved_at`, and advances `ReportStatus` to `RESOLVED`.
- `reject_report(db, report_id, rejection_reason, notes, suggested_department)`: Enforces structured reason and notes, marks assignment `REJECTED`, transitions `ReportStatus` from `ASSIGNED` back to `PRIORITIZED`, flags `reassignment_required = True`, and preserves historical department for triage review.
- `get_assignment_history(db, report_id)`: Fetches complete chronological audit trail of all assignment attempts.

### 4. System-Wide Influence Matrix
The Department entity is not an isolated CRUD table—it directly influences all layers of the CivicSense ecosystem:

| Domain / Subsystem | How Department Influences This Domain |
| :--- | :--- |
| **Report Lifecycle & State Machine** | Acts as the operational execution engine between administrative triage (`PRIORITIZED`) and physical remediation (`RESOLVED`). Drives state transitions (`PRIORITIZED` → `ASSIGNED` → `IN_PROGRESS` → `RESOLVED`). Governs the non-destructive rejection loop (`ASSIGNED` → `PRIORITIZED` with `reassignment_required=True`), preventing valid civic reports from being discarded due to departmental misrouting. |
| **Authority Dashboard** | Powers dedicated Department Operations Hub (`/departments`) and Department Workspace (`/departments/:code`) with live job queues and 5-metric workload counters. Real-time TanStack Query polling (5s) keeps department queues fresh. Prominently displays "Department Reassignment Required" alert banners on `ReportDetailPage`. Renders immutable "Department Assignment History" cards with officer names, timestamps, rejection reasons, and completion notes. Adds Department filter to global reports queue and map. |
| **Citizen Mobile App (Android & Expo)** | Directly influences citizen transparency and trust: Stage 4 of the 6-stage resolution timeline displays the assigned division (`"Assigned to [Department Name]."`). If a department declines a ticket (`reassignment_required=True`), Stage 3 transparently informs the citizen (`"Triage team is reassigning issue to the appropriate division."`) without alarming them with internal rejection jargon. Polling sync keeps citizen devices updated in near-real-time. |
| **AI & Decision Engine** | Feeds category-to-department recommendation rules during triage. Determines baseline SLA calculation windows based on `Department.sla_hours_default` (e.g., 24h for Sanitation vs 48h for Roads). Enables human-in-the-loop verification of both category classification and proposed department routing. |
| **Data Mining & Analytics (Academic Domain 3)** | **Cross-Department Defect Correlation**: Discovers systemic inter-departmental root causes (e.g., Water pipeline excavation by Water Dept causing recurring pothole complaints for Roads Dept; or garbage dumping blocking stormwater drainage).<br>**Operational Bottleneck Mining**: Measures acknowledgment latency, repair lead times, and SLA breach rates across municipal divisions.<br>**Jurisdictional Ambiguity Mining**: Analyzing high rejection rates per category pinpoints municipal gray areas (e.g. roadside tree branches between Electrical Dept and Forest/Public Works) requiring policy or classification adjustments. |

---

## 24. Data Model (conceptual)

```
Report
------
report_id (UUID)
tracking_id (unique human-readable string, e.g. REP-YYYYMM-XXXXXX)
citizen_id (installation-scoped identifier / anonymous token)
citizen_name, citizen_phone, citizen_email, citizen_postal_code (privacy-controlled)
timestamp
latitude, longitude
category (citizen-selected / verified)
description
department_id (FK -> Department.id, nullable)
department (cached department name string)
assigned_officer (current assignee name/ID)
reassignment_required (boolean flag)
image_reference, image_hash
image_embedding, text_embedding
local_prediction, server_prediction
confidence, severity, priority
status (11-state enum), verification_status, verification_result
issue_id (FK -> Issue.id, real-world defect grouping)
created_at, updated_at

Department
----------
id (UUID)
name (unique string, e.g. "Roads & Bridges")
code (unique slug, e.g. "ROADS")
description (jurisdiction scope)
head_name (division lead)
contact_email, contact_phone
sla_hours_default (integer default SLA hours)
is_active (boolean)
created_at, updated_at

ReportAssignment
----------------
id (UUID)
report_id (FK -> Report.id)
department_id (FK -> Department.id)
department_name (snapshot string)
assigned_by (triage officer / system)
assigned_to_officer (field officer / crew lead)
status (ASSIGNED | IN_PROGRESS | COMPLETED | REJECTED)
rejection_reason (OUT_OF_JURISDICTION | INSUFFICIENT_ACCESS | DUPLICATE_WORK_ORDER | REQUIRES_MAJOR_BUDGET | INSUFFICIENT_INFORMATION | OTHER)
notes (dispatch instructions, remediation notes, or rejection explanation)
created_at, resolved_at
```

**Suggested entities:** User, Report, ReportEvidence, AIAnalysis, Verification, Department, ReportAssignment, IssueGroup (Issue), Location, Resolution, ModelVersion, FeedbackEvent.

Data mining should ideally operate on **analytical views** derived from these tables rather than being tightly coupled to transactional tables. Schema evolves during implementation.

---

## 25. Vector Storage

Used for: similar image search, similar text search, duplicate detection, related-report discovery.

```
New Report Vector → Vector Index → Nearest Neighbors → Potentially Related Reports
```

Choose a vector-capable storage solution that fits the implementation environment. Combine vector results with geographic/temporal constraints — don't trust vector similarity alone.

---

## 26. Server vs Mobile Responsibility Summary

| Mobile | Server |
|---|---|
| Capture | Stronger inference |
| Validation | Multimodal fusion |
| Preprocessing | Similarity search |
| Lightweight inference | Duplicate detection |
| Representation | Severity |
| GPS | Priority |
| Payload creation | Historical context |
| | Human routing |
| | Data mining |
| | Analytics |
| | Model management |

This separation is intentional and should not be casually changed.

---

## 27. Why Edge AI? (and the honest caveat)

**Potential benefits:** reduced raw-image transfer, lower server inference workload, lower bandwidth, potentially lower latency, better behavior under limited connectivity, more privacy-conscious architecture, distributed computation.

**But this must be measured, not assumed.** The project must experimentally compare Cloud-only vs Hybrid Edge-Cloud on:

| Metric | Cloud-only | Hybrid |
|---|---|---|
| Upload payload size | Measure | Measure |
| Mobile inference time | N/A | Measure |
| Server inference time | Measure | Measure |
| End-to-end latency | Measure | Measure |
| Mobile memory usage | N/A | Measure |
| Server workload | Measure | Measure |
| Accuracy | Measure | Measure |
| Network usage | Measure | Measure |

**Never claim:** "On-device processing is always better."
**Instead claim:** "CivicSense investigates whether moving suitable preprocessing and lightweight inference to the edge can reduce communication and server-side processing while maintaining acceptable accuracy and latency." — this is the stronger, defensible research statement.

---

## 28. Privacy Architecture

System handles location, photographs, descriptions, timestamps.

```
Data minimization → Encryption → Access control
  → Limited evidence exposure → Retention policy
```
Avoid exposing exact citizen locations publicly unless required.

---

## 29. Abuse and Spam Handling

**Signals to watch:** submission frequency + image similarity + text similarity + location consistency + temporal patterns → suspicious reports routed to verification.

**Do not** implement an opaque "citizen trust score" unless there's enough data to justify it.

---

## 30. Out-of-Distribution / Unknown Issues

If the model sees something it wasn't trained on (e.g. Pothole 0.31, Road crack 0.28, Garbage 0.12) — **don't force a confident category.** Route to `UNKNOWN / OTHER / REVIEW_REQUIRED`.

### Confidence Calibration
Confidence values should be evaluated, not blindly trusted — check whether predictions at ~95% confidence are actually correct ~95% of the time. This determines the automatic-vs-human-review threshold.

---

## 31. MLOps

```
Dataset → Validation → Training → Evaluation → Versioning
  → Deployment → Monitoring → Human Feedback → Retraining → New Model
```

Every prediction records: model name, model version, preprocessing version, embedding version, timestamp (e.g. `vision-mobile-v1`, `vision-server-v2`, `text-classifier-v1`, `fusion-model-v1`).

### Model Improvement Loop
```
Production → Predictions → Human Corrections → Verified Dataset
  → Evaluation → Candidate Model → Compare with Current Model
  → Deploy only if better
```
**Never** auto-replace a production model just because a new one exists.

---

## 32. AI Systems Engineering Scope

Represented through the full software lifecycle: OOP design, requirements, architecture, UML, Agile/Scrum, API design, testing, deployment, MLOps, monitoring, human-in-the-loop, maintainability.

### UML Deliverables
- **Use Case Diagram** — actors: Citizen, Triage Officer, Department Officer/Admin, Municipal Inspector, Reviewer, Administrator, ML/MLOps System
- **Class Diagram** — core entities: User, Report, Evidence, AIAnalysis, Verification, Department, ReportAssignment, IssueGroup (Issue), Resolution, ModelVersion
- **Activity Diagram** — citizen report processing and municipal department remediation
- **Sequence Diagram** — Citizen → Mobile App → API → AI Pipeline → Triage Officer → Department Dispatch → Department Remediation → Inspector Verification → Database → Dashboard
- **State Chart** — 11-stage report lifecycle with department operational loops (assignment, acknowledgment, completion, rejection & reassignment)

---

## 33. Agile Development — Suggested Sprints

| Sprint | Focus |
|---|---|
| 1 | Requirements + architecture + UML |
| 2 | Mobile reporting workflow |
| 3 | Image processing / vision baseline |
| 4 | Text analytics baseline |
| 5 | Server fusion and decision engine |
| 6 | Human review + lifecycle |
| 7 | Data mining + dashboard |
| 8 | Edge optimization + MLOps + evaluation |

Exact plan can flex — but keep this order.

---

## 34. Recommended Technology Direction

- **Mobile:** React Native / Native Android (Kotlin) + a suitable mobile ML runtime
- **Backend:** Python + FastAPI
- **Vision:** Python, OpenCV, PyTorch (research/training), lightweight YOLO-family or equivalent, ONNX/LiteRT for mobile deployment
- **Text:** Python, scikit-learn, NLTK, spaCy, sentence embedding model where justified
- **Data Mining:** pandas, NumPy, scikit-learn, a frequent-pattern-mining library
- **Database:** PostgreSQL + vector-capable extension/index
- **Dashboard:** React / Next.js + map visualization library

Choices depend on team familiarity and required native ML capabilities — finalize after feasibility testing.

---

## 35. Infrastructure Philosophy

Design for **modest infrastructure**. No expensive GPU prerequisite. Use local CPU/GPU where available, small cloud instances if needed, pre-trained models, transfer learning, lightweight/quantized inference. A large production GPU cluster is outside academic prototype scope.

---

## 36. Dataset Strategy

Use public datasets where suitable — a road-damage dataset such as **RDD2022** can be a starting point.

```
Find suitable public dataset → Check license → Check annotations
  → Check category coverage → Check diversity → Use/adapt if appropriate
```
If no suitable public dataset exists for a category, curate a small project-specific one.

**Evaluate before training:** number of images, class distribution, annotation quality, geographic/lighting/weather/device diversity, licensing, train/val/test separation (avoid leakage).

---

## 37. Evaluation Strategy

- **Vision:** precision, recall, F1, mAP, IoU (where applicable), confusion matrix, inference latency
- **Text:** accuracy, precision, recall, F1, confusion matrix
- **Multimodal:** category accuracy, severity accuracy, conflict detection rate, human-review routing performance
- **Similarity:** duplicate detection precision/recall (where labeled data exists), similarity threshold evaluation
- **Data Mining:** cluster quality, pattern support/confidence, interpretability, practical usefulness
- **Edge:** mobile latency, memory usage, payload size, network reduction, accuracy difference vs cloud-only

---

## 38. Major Technical Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Mobile model too heavy | Smaller model, quantization, reduced input size, benchmark on real devices |
| Embedding incompatibility | Version every embedding model, preserve evidence, maintain model metadata |
| Fusion doesn't improve accuracy | Establish image-only/text-only baselines first, compare experimentally, don't assume fusion wins |
| Insufficient datasets | Reduce category count, use transfer learning, curate a small domain dataset |
| False severity estimates | Separate confidence/severity, use explainable scoring factors, route high-impact to humans |
| Duplicate detection errors | Combine vector similarity with geographic/temporal constraints, validate thresholds experimentally |
| Scope explosion | Keep MVP small, treat advanced integrations as future work |

---

## 39. Recommended MVP

```
Mobile App → Image+Text+GPS → Basic Edge Image Processing
  → Server Vision Model → Text Classification → Multimodal Fusion
  → Category → Severity → Priority → Human Review
  → Database → Authority Dashboard
```
Then layer on: duplicate detection → geospatial hotspots → frequent patterns → temporal analysis → MLOps feedback → edge optimization.

---

## 40. Suggested Development Order (do not skip ahead)

1. **Baselines:** Image → Vision model → Category (separately) · Text → Text model → Category (separately)
2. **Multimodal:** Image + Text → Fusion → Category — compare against the individual baselines
3. **Decision layer:** add Confidence, Severity, Priority
4. **Human loop:** add Review, Correction, Verification
5. **Historical intelligence:** add Duplicates, Hotspots, Patterns, Trends
6. **Edge optimization:** move suitable preprocessing/inference to mobile and benchmark
7. **MLOps:** model versioning, evaluation, feedback, retraining workflow

**Do not begin by trying to build the entire architecture at once.**

---

## 41. Research Questions

- **RQ1:** Can lightweight image processing/inference run effectively on consumer mobile devices for selected civic categories?
- **RQ2:** Does combining visual and textual evidence improve classification vs a single modality?
- **RQ3:** Can multimodal disagreement identify reports needing human verification?
- **RQ4:** Can historical reports improve prioritization via recurrence, frequency, and spatial info?
- **RQ5:** Can edge processing reduce communication/server workload while maintaining acceptable performance?

---

## 42. Subject-to-Feature Mapping

**AI Systems Engineering:** OOP, SDLC, Agile, UML, Architecture, Design Patterns, MLOps, Testing, Deployment, Human-in-the-loop

**Machine Vision & Pattern Recognition:** Image preprocessing, filtering, segmentation, morphology, texture, color, shape, feature extraction, pattern recognition, classification, object detection, similarity, edge inference

**Data Mining & Text Analytics:** Data preprocessing, text preprocessing, tokenization, stemming, lemmatization, TF-IDF, N-grams, word embeddings, text classification, clustering, frequent pattern mining, correlation, temporal analysis, spatial analysis

---

## 43. Architecture Summary

```
                CITIZEN MOBILE (Image, Text, GPS, Timestamp)
                             │
                             ▼
                  EDGE AI LAYER (preprocessing, features,
                  lightweight AI, quality check)
                             │
                             ▼
                         API LAYER
                             │
                             ▼
               SERVER AI (Vision, Text, Fusion,
               Similarity, Duplicate detection)
                             │
                             ▼
               DECISION ENGINE (Category, Confidence,
               Severity, Priority, Conflict)
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
           AUTOMATIC PROCESSING    HUMAN REVIEW
                  │                     │
                  └──────────┬──────────┘
                             ▼
               CENTRAL TRIAGE & PRIORITIZATION
                             │
                             ▼
               MUNICIPAL DEPARTMENT DISPATCH
       (Roads, Waste, Water, Electrical, Planning, etc.)
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   FIELD ACKNOWLEDGE & REMEDIATION    DEPARTMENT REJECTION
        (In Progress → Resolved)      (Return to Prioritized
            │                         reassignment_required=True)
            ▼                                 │
   RESOLUTION VERIFICATION                    │
   (Inspector review → Closed)                │
            │                                 │
            └───────────────┬─────────────────┘
                            ▼
                  CIVIC DATABASE (Reports, Evidence,
                  Verification, Departments, Assignments,
                  Resolutions, Model versions)
                            │
                            ▼
                  DATA MINING (Hotspots, Clustering,
                  Trends, Patterns, Correlations, Lead-times)
                            │
                            ▼
            AUTHORITY DASHBOARD & DEPARTMENT WORKSPACES
            (Queue, Map, Analytics, SLAs, Live Polling)
                            │
                            ▼
                  RESOLUTION → FEEDBACK → MLOps
                            │
                            └──────────► MODEL IMPROVEMENT
```

---

## 44. Engineering Rules for AI Coding Agents

1. **Do not change the architecture casually** — the edge/server separation is intentional.
2. **Embeddings are never interchangeable** — every embedding must carry model name, version, dimension, preprocessing version.
3. **Never confuse confidence with severity** — separate fields, separate concepts.
4. **AI is never the final authority** — high-risk/uncertain decisions must support human verification.
5. **Preserve evidence** — never delete original evidence just because an embedding exists.
6. **No AI for decoration** — every model must solve a defined problem.
7. **Establish baselines first** — before complex multimodal models.
8. **Measure before claiming improvement** — no claiming edge/fusion/embeddings/a model is "better" without experimental evidence.
9. **Keep the MVP small** — a working pipeline for a few categories beats an incomplete system covering everything.
10. **Keep modules independently replaceable** — vision, text, fusion, decision, data mining, MLOps communicate through explicit interfaces.
11. **Separate prediction from decision** — `ML Prediction → Decision Engine → Operational Decision`.
12. **Separate report from issue** — multiple reports can map to one real-world issue.
13. **Never force uncertain predictions into a category** — use `UNKNOWN/OTHER/REVIEW_REQUIRED`.
14. **Record model provenance on every AI result.**

---

## 45. Recommended Service Boundaries

```
mobile/
    capture, preprocessing, edge_inference, embedding, report_submission

backend/
    api, report_service, vision_service, text_service, fusion_service,
    similarity_service, decision_service, verification_service, analytics_service

ml/
    datasets, preprocessing, training, evaluation, model_registry

data/
    database, vector_index, evidence_storage

dashboard/
    reports, map, analytics, verification, resolution
```
Conceptual boundaries — not mandatory exact folder names.

---

## 46. Conceptual API Payload

```json
{
  "report_id": "generated-id",
  "timestamp": "ISO-8601",
  "location": { "latitude": 0.0, "longitude": 0.0 },
  "image": {
    "embedding": [],
    "local_prediction": { "label": "pothole", "confidence": 0.91 },
    "quality": 0.87,
    "model_version": "vision-mobile-v1"
  },
  "text": {
    "representation": [],
    "preprocessing_version": "text-v1"
  },
  "evidence_reference": "secure-reference"
}
```
Exact schema finalized during implementation.

---

## 47. Security & Observability

**Security:** HTTPS, authentication, authorization, input validation, file validation, rate limiting, secure evidence access, database/vector-index access control, audit logging. Never expose unrestricted evidence or admin APIs.

**Observability metrics:** mobile inference latency, server inference latency, end-to-end latency, model confidence distribution, human-review rate, conflict rate, duplicate detection rate, API errors, queue length, model version usage.

---

## 48. Explainability

Instead of `Priority = 0.94`, show:

```
HIGH PRIORITY
Reasons:
✓ High severity
✓ 12 related reports
✓ Near school
✓ Safety concern mentioned
✓ Previous unresolved reports
```
The displayed reasons must reflect actual model/decision inputs — no fake explanations.

---

## 49. Important Distinctions Recap

- **Prediction vs Decision:** ML output feeds a Decision Engine, which produces the operational/business decision. Keep these layers separate for debugging, explainability, testing, and model swaps.
- **Detection vs Verification:** AI says "this *appears* to be a pothole" → Human says "*confirmed*, it is a pothole" → DB records "verified civic issue."
- **Report vs Issue:** many reports, one underlying issue.
- **Issue vs Resolution:** an issue persists in history even after it's resolved — don't delete it, just update its status.

---

## 50. Potential Future Extensions (post-MVP only)

Weather-data correlation, traffic-data integration, OpenStreetMap road context, accident-data integration, municipal open-data integration, multilingual descriptions, voice-based reporting, offline-first reporting, more civic categories, automated authority ticket creation, advanced multimodal foundation models, active learning, federated learning, privacy-preserving analytics.

---

## 51. Strongest Novelty / Differentiation

**Not this:** "We made an AI that detects potholes."

**This:** the *system integration* —

```
Edge Processing + Multimodal Evidence + Conflict Detection
  + Similarity/Duplicate Detection + Severity + Priority Ranking
  + Human Verification + Historical Data Mining
  + Geospatial Intelligence + MLOps Feedback
```

The research/engineering value is in how these components work together as a practical civic intelligence pipeline — not any single model.

---

## 52. Final Project Definition

**One-line:** CivicSense is a hybrid edge-cloud multimodal AI system that transforms citizen-submitted images, descriptions, and locations into verified, prioritized, and historically analyzable civic issues.

**Short technical:** CivicSense performs privacy-conscious preprocessing and lightweight visual inference on mobile devices, sends compact representations and structured metadata to server-side AI services, combines visual, textual, geographical, and historical evidence, assigns category/severity/priority, routes uncertain cases to human reviewers, and applies data mining to discover civic hotspots, recurring problems, trends, and frequent patterns.

**Full conceptual:** CivicSense is an AI-assisted civic decision-support platform designed around a complete report-to-resolution lifecycle. A citizen captures an image of a civic problem and describes it in natural language while the mobile device automatically attaches location and timestamp. Suitable image preprocessing, feature extraction, lightweight inference, and text preprocessing happen at the edge to reduce unnecessary communication and server-side load. The server performs stronger vision and language analysis, multimodal evidence fusion, similarity search, duplicate detection, severity estimation, and priority ranking. Reports with low confidence, conflicting modalities, critical severity, or other defined uncertainty conditions route to human reviewers. Verified reports become structured historical data, from which Data Mining discovers geospatial hotspots, temporal trends, recurring issues, clusters, and frequent problem combinations. Resolution status and human corrections feed back into the system, supporting model evaluation, versioning, and future improvement via an MLOps workflow.

---

## 53. Final Mental Model for Developers

```
WHAT DID THE CITIZEN SEND?
          ↓
   EDGE PROCESSING
          ↓
   WHAT DOES IT MEAN?
          ↓
   SERVER-SIDE AI
          ↓
DO THE SOURCES AGREE? ──NO──► HUMAN REVIEW
          │YES
          ▼
   HOW SERIOUS?
          ↓
   HOW URGENT?
          ↓
WHAT ELSE EXISTS AROUND IT?
          ↓
     DATA MINING
          ↓
   WHAT CAN WE LEARN?
          ↓
WHAT SHOULD HUMANS DO?
          ↓
    RESOLUTION
          ↓
WHAT DID WE LEARN FROM IT?
          ↓
       MLOps
```

---

## 54. Final Engineering Principle

CivicSense should be built as a **measurable AI system**, not a collection of AI features. Every component needs: a defined responsibility, a measurable input, a measurable output, a clear interface, a baseline, an evaluation method, and a reason for existing.

**Prefer:** simple + measurable + replaceable
**Over:** complex + impressive-looking + impossible to evaluate

---

## 55. Canonical Project Statement

**CivicSense — From Citizen Reports to Civic Intelligence**

A hybrid edge-cloud multimodal AI platform that uses Machine Vision, Text Analytics, Data Mining, and AI Systems Engineering to transform unstructured citizen reports into verified, prioritized, and actionable civic intelligence — while preserving human oversight and enabling continuous system improvement.
