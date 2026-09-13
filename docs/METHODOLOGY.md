# CivicSense — Methodology

## 1. Report Ingestion

Citizens submit reports through the mobile application or API. Each submission includes:
- Free-text description of the civic issue
- Category selection (Pothole, Road Damage, Garbage, Water Leakage, Broken Streetlight, Other)
- GPS coordinates (latitude, longitude)
- Optional evidence images (base64-encoded)
- Optional citizen contact information

The backend validates the payload against Pydantic v2 schemas, checks location ranges (-90 to 90 latitude, -180 to 180 longitude), verifies text length limits, and assigns a unique tracking ID (`REP-YYYYMM-XXXXXX`). Evidence images are decoded, hashed (SHA-256), and stored on disk.

**Status:** IMPLEMENTED

## 2. Validation and Normalization

Report inputs undergo strict validation:
- Location coordinates must be within valid geographic ranges
- Description must be between 3 and 5000 characters
- Category must be one of the canonical civic issue types
- Evidence images are checked for file size limits, decompression bomb protection, and MIME type validation
- GPS coordinates near (0, 0) are flagged as Null Island failures

**Status:** IMPLEMENTED

## 3. Text Embedding

The system uses `sentence-transformers/all-MiniLM-L6-v2` to generate 384-dimensional dense text embeddings:
- Tokenization with attention masks
- Mean pooling over token embeddings
- L2 unit-norm projection
- Embedding stored as JSON in the database

The model runs on CPU without GPU requirements. Cold-start load time is approximately 90ms; per-report inference is approximately 10ms.

**Status:** IMPLEMENTED

## 4. Similarity Comparison

For each incoming report, the system searches for existing issues within a configurable radius (default: 50 meters):
- **Text similarity**: Cosine similarity between the report embedding and the issue centroid embedding
- **Spatial proximity**: Haversine distance scored with linear decay (0m → 1.0, 50m → 0.0)
- **Category compatibility**: Exact match (1.0), bridge categories (0.5), or mismatch (0.0)

The combined score is computed as:
```
combined_score = 0.40 * text_similarity + 0.35 * distance_score + 0.25 * category_score
```

**Status:** IMPLEMENTED

## 5. Category Compatibility

Categories are compared using a predefined compatibility matrix:
- **Exact match** (1.0): Same explicit category (e.g., both "Pothole")
- **Bridge** (0.5): Related categories (configurable pairs)
- **Mismatch** (0.0): Different categories

**Safety gate:** When both the report and the candidate issue have explicit, non-`Other` categories that differ, the action is forced to `NEW_ISSUE` regardless of text or spatial proximity. This prevents false auto-merges between co-located but distinct defect types.

**Status:** IMPLEMENTED

## 6. Spatial Compatibility

Reports are compared using Haversine great-circle distance on WGS84 coordinates:
- Reports within the configured radius receive a linearly decaying distance score
- Reports beyond the radius receive a distance score of 0
- Null Island coordinates (0, 0) are rejected to prevent GPS-failed reports from clustering

**Status:** IMPLEMENTED

## 7. Decision Thresholds

The combined similarity score determines the match action:

| Score Range | Action | Description |
|---|---|---|
| ≥ 0.70 | AUTO_LINK | Report is automatically linked to the existing issue |
| 0.45 – 0.70 | CANDIDATE | Match is routed to human officer review |
| < 0.45 | NEW_ISSUE | A new issue entity is created |

These thresholds are provisional heuristics, not scientifically validated.

**Status:** IMPLEMENTED

## 8. Candidate Review

CANDIDATE matches are presented to municipal triage officers through the dashboard. Officers can:
- **Approve**: Confirm the report represents the same underlying issue
- **Reject**: Keep the report as an independent issue
- **Reject and relink**: Reject the candidate and link the report to a different issue

All review decisions are audit-logged with reviewer identity, optional notes, and timestamps. Already-reviewed matches cannot be re-reviewed (409 MATCH_ALREADY_REVIEWED).

**Status:** IMPLEMENTED

## 9. Issue Aggregation

Approved reports are linked to a canonical issue entity. The issue tracks:
- Total report count
- Unique citizen reporters
- Category and status
- Geographic centroid (average of linked report coordinates)
- Creation and update timestamps

Multiple reports from different citizens about the same pothole, for example, are aggregated into a single issue cluster.

**Status:** IMPLEMENTED

## 10. Priority Scoring

Issue priority is computed from five weighted factors:

| Factor | Weight | Description |
|---|---|---|
| Severity | 0.30 | Physical risk of the defect (keyword heuristic) |
| Report volume | 0.25 | Number of linked reports (saturation curve) |
| Unique reporters | 0.20 | Distinct citizens reporting (public impact) |
| Recency | 0.15 | Time since most recent report (exponential decay) |
| Persistence | 0.10 | Days since issue creation |

The weighted sum produces a score from 0 to 100, mapped to priority levels:
- CRITICAL ≥ 65
- HIGH ≥ 40
- MEDIUM ≥ 15
- LOW < 15

Priority is automatically recomputed when reports are linked or matches are approved.

**Status:** IMPLEMENTED

## 11. Audit Trail

Every match decision is recorded in the `report_issue_matches` table with:
- Report and issue references
- Similarity score and component breakdown
- Match action (AUTO_LINK, CANDIDATE, NEW_ISSUE)
- Reviewer identity and notes
- Timestamps for creation and review

This provides full traceability for municipal accountability.

**Status:** IMPLEMENTED

## 12. Dashboard Presentation

The web dashboard provides:
- Prioritized issue queues
- Candidate match review interface with evidence panels
- Interactive map visualization
- Department workload tracking
- AI pipeline status monitoring
- Real-time polling (5–10 second intervals)

**Status:** IMPLEMENTED

## Future Work (Not Implemented)

- Image-based issue classification (MobileNetV3 pilot complete, not integrated)
- Multimodal fusion of text and vision signals
- Production-grade authentication and RBAC
- pgvector-based efficient similarity search
- Real-time notifications and citizen tracking
- Multilingual report support
