# CivicSense — Presentation Outline

**Duration:** 15–20 minutes + 5–8 minute demo

---

## Slide 1: Title

**CivicSense — From Citizen Reports to Civic Intelligence**

- AI-assisted civic issue reporting and aggregation platform
- Bridges citizen reports with municipal operational response
- Human-in-the-loop decision support, not autonomous authority

*Suggested visual:* CivicSense logo + tagline

---

## Slide 2: Problem Statement

- Millions of citizen civic reports received annually by municipalities
- Duplicate complaints waste resources and inflate problem volumes
- Fragmented reports across channels obscure recurring issues
- Manual triage is slow, inconsistent, and does not scale
- Lack of prioritization leads to misallocated resources
- Limited operational visibility for municipal managers

*Suggested visual:* Flowchart showing fragmented report intake → overwhelmed triage → delayed response

---

## Slide 3: Motivation and Existing Challenges

- Existing systems treat each report independently
- No automated deduplication or related-report detection
- No explainable priority scoring
- Human reviewers lack AI-assisted triage tools
- Gap between citizen submission and municipal resolution
- Need for transparent, auditable decision-making

*Suggested visual:* Comparison table: Current approach vs. CivicSense approach

---

## Slide 4: Proposed Solution

- Text semantic similarity for duplicate detection
- Geospatial proximity analysis for co-located reports
- Category compatibility checking with safety gates
- 3-tier match routing: AUTO_LINK / CANDIDATE / NEW_ISSUE
- Human-in-the-loop review for uncertain cases
- Explainable priority scoring from multi-factor weighted formula

*Suggested visual:* High-level system flow diagram

---

## Slide 5: System Architecture

- **Mobile App**: Citizen report submission with evidence capture
- **Backend API**: FastAPI with 29 REST endpoints
- **PostgreSQL**: Relational data store with 10 versioned migrations
- **MiniLM Model**: 384-dim text embeddings for semantic similarity
- **Similarity Engine**: Weighted text + spatial + category scoring
- **Priority Engine**: 5-factor weighted priority calculation
- **Dashboard**: React + TypeScript authority operations portal

*Suggested visual:* Mermaid architecture diagram (see `docs/ARCHITECTURE.md`)

---

## Slide 6: AI/Similarity Processing Pipeline

1. Report ingestion and validation
2. Text embedding generation (MiniLM-L6-v2)
3. Spatial candidate search (50m radius)
4. Category compatibility check
5. Combined similarity scoring (0.40 text + 0.35 spatial + 0.25 category)
6. 3-tier routing decision
7. Human review for CANDIDATE matches
8. Issue aggregation and priority recomputation

*Suggested visual:* Pipeline flowchart with component weights

---

## Slide 7: Human-in-the-Loop Review

- CANDIDATE matches (45%–70% confidence) require human review
- Officers see full evidence: text similarity, spatial distance, category match
- Three actions: Approve (link), Reject (independent), Reject + Relink (alternate issue)
- All decisions audit-logged with reviewer identity and timestamps
- 409 protection prevents duplicate reviews
- System is decision-support, not autonomous authority

*Suggested visual:* Screenshot of candidate match review interface

---

## Slide 8: Priority Scoring and Explainability

- **Severity** (0.30): Physical risk of the defect
- **Report volume** (0.25): Number of linked reports
- **Unique reporters** (0.20): Distinct citizens affected
- **Recency** (0.15): Time since most recent report
- **Persistence** (0.10): Duration of ongoing issue
- Output: 0–100 score → CRITICAL / HIGH / MEDIUM / LOW
- Full breakdown available for audit and explainability

*Suggested visual:* Priority breakdown chart for a sample issue

---

## Slide 9: Dashboard and Demonstration

- Live demo of the authority dashboard
- AI Operations → Candidate Duplicate Reviews tab
- Show 6 pending candidate matches from pilot dataset
- Demonstrate approve and reject actions
- Show priority recomputation and audit trail

*Suggested visual:* Live demo or screenshots

---

## Slide 10: Evaluation Results

- **470 backend tests**, **85 frontend tests** — all passing
- Synthetic duplicate detection: 100% precision, 100% recall, F1 = 1.0000
- Text model lift: MiniLM +8.33pp over deterministic baseline (p = 0.0001)
- Selective auto-triage: 27% of reports auto-accepted with 100% accuracy
- Human review safely handles all uncertain cases

*Suggested visual:* Bar chart comparing model accuracies

---

## Slide 11: Limitations and Ethical Considerations

- Prototype authentication only (not production-ready)
- Synthetic-only evaluation metrics (not real-world validated)
- Text-only similarity (no image classification integrated)
- GPS jitter and 50m spatial cutoff
- Severity is keyword-heuristic, not ML-classified
- No real municipal deployment or government integration
- System assists human decision-makers, does not replace them

*Suggested visual:* Limitations table

---

## Slide 12: Future Scope and Conclusion

- **P0**: Real authentication (JWT/RBAC), PostgreSQL validation, rate limiting
- **P1**: Image classification integration, real-world evaluation dataset, browser E2E
- **P2**: Multilingual support, real-time notifications, advanced geospatial clustering
- CivicSense demonstrates that AI-assisted deduplication and prioritization can improve civic issue response
- Human-in-the-loop design ensures accountability and trust
- Open for academic evaluation and controlled pilot deployment

*Suggested visual:* Roadmap timeline
