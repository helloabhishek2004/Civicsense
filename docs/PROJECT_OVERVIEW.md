# CivicSense — Project Overview

**Project Name:** CivicSense — From Citizen Reports to Civic Intelligence

**Problem Being Addressed:**
Municipal authorities receive large volumes of citizen-reported civic issues (potholes, garbage dumping, water leakage, broken streetlights, etc.) through various channels. These reports are often fragmented, duplicated, and manually triaged, leading to delayed response times, missed recurring issues, and poor operational visibility.

**Intended Users:**
- Citizens: Report civic issues with evidence and location
- Triage Officers: Review, prioritize, and route incoming reports
- Department Managers: Assign and track field resolution work
- System Administrators: Monitor platform health and AI pipeline performance

**Core Workflow:**
1. Citizen submits a report with description, category, photo, and GPS location
2. Backend validates and normalizes the submission
3. Text embedding model generates a semantic representation
4. Similarity engine compares against existing issues using text, spatial, and category signals
5. High-confidence matches are auto-linked; uncertain matches are routed to human review
6. Officers approve or reject candidate matches through the dashboard
7. Approved reports are aggregated into issue clusters
8. Priority scores are computed from severity, volume, recency, and persistence
9. Municipal departments receive prioritized work assignments

**Main Technologies:**
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.0, PostgreSQL 16
- Frontend: React 18, TypeScript, Vite, Tailwind CSS, TanStack Query
- Mobile: Kotlin + Jetpack Compose (Android), React Native + Expo (scaffold)
- AI/ML: sentence-transformers/all-MiniLM-L6-v2, PyTorch
- Infrastructure: Docker Compose, Alembic migrations

**AI-Assisted Functionality:**
- Text semantic similarity using MiniLM sentence embeddings (384-dim)
- Geospatial proximity analysis using Haversine distance
- Category compatibility scoring
- Automated 3-tier match routing (AUTO_LINK / CANDIDATE / NEW_ISSUE)
- Dynamic priority ranking from multi-factor weighted scoring

**Human-in-the-Loop Design:**
- CANDIDATE matches (45%–70% confidence) require human officer review
- Officers approve (confirm linkage) or reject (keep independent)
- Officers can reject and relink to an alternate issue
- All decisions are audit-logged with reviewer identity, notes, and timestamps
- Already-reviewed matches return 409 MATCH_ALREADY_REVIEWED

**Current Implementation Status:**
- 470 backend tests passing
- 85 frontend tests passing
- 12 Alembic migrations (0001–0010)
- 29 REST API endpoints
- 40-report synthetic pilot dataset
- 6 pending + 4 rejected candidate matches
- Prototype-only authentication (X-Reviewer-ID header)
- No image classification integrated (text-only similarity)
- No production deployment
