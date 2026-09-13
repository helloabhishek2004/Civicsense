# CivicSense — System Objectives

## Primary Objectives

### 1. Accept Structured Civic Issue Reports
- Receive citizen submissions with description, category, GPS coordinates, and optional evidence
- Validate all inputs against schema constraints (location ranges, text length, category values)
- Assign unique tracking IDs and initialize lifecycle status
- Preserve raw evidence with cryptographic hashes for audit integrity

### 2. Normalize and Process Report Content
- Generate semantic text embeddings using a sentence transformer model
- Extract category, location, and temporal features
- Store provenance metadata (model version, preprocessing version)
- Support degraded mode when the embedding model is unavailable

### 3. Identify Potentially Related Reports
- Compare incoming reports against existing issues using:
  - **Text similarity**: Cosine similarity of MiniLM embeddings
  - **Spatial proximity**: Haversine distance within a configurable radius
  - **Category compatibility**: Exact match, bridge categories, or mismatch
- Generate a combined similarity score using weighted components

### 4. Avoid Unsafe Automatic Merges
- Force NEW_ISSUE when categories explicitly conflict (e.g., pothole vs. streetlight)
- Reject Null Island coordinates (0, 0) to prevent GPS-failed reports from clustering
- Require minimum similarity thresholds for any automated linkage
- Preserve human oversight for all uncertain decisions

### 5. Route Uncertain Matches to Human Review
- Classify matches into three tiers:
  - AUTO_LINK (≥ 0.70): Automatic issue linkage
  - CANDIDATE (0.45 – 0.70): Human review required
  - NEW_ISSUE (< 0.45): Create new issue
- Present candidate matches with full evidence (text, spatial, category signals)
- Support approve, reject, and reject-with-relink actions

### 6. Aggregate Reports into Issue Clusters
- Link multiple reports to a single canonical issue entity
- Track report counts, unique reporters, and temporal spread
- Maintain separation between individual reports and aggregated issues

### 7. Calculate Explainable Priority Scores
- Compute priority from five weighted factors:
  - Severity (0.30): Physical risk of the defect
  - Report volume (0.25): Number of linked reports (saturation curve)
  - Unique reporters (0.20): Distinct citizens reporting
  - Recency (0.15): Time since most recent report (exponential decay)
  - Persistence (0.10): Days since issue creation
- Map computed score to priority levels: CRITICAL, HIGH, MEDIUM, LOW
- Provide full breakdown for audit and explainability

### 8. Preserve Review Decisions Through an Audit Trail
- Record every match decision (AUTO_LINK, CANDIDATE, NEW_ISSUE)
- Store reviewer identity, notes, timestamps, and decision rationale
- Prevent duplicate reviews (409 MATCH_ALREADY_REVIEWED)
- Maintain immutable history of all approval and rejection events

### 9. Provide an Operational Dashboard
- Display prioritized issue queues with real-time updates
- Show candidate match review interface with evidence panels
- Visualize issues on an interactive map
- Track department workloads and assignment lifecycle
- Present AI pipeline status and processing metrics
