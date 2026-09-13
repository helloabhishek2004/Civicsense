# CivicSense — Portfolio Description

## Project

**CivicSense** — AI-assisted civic issue reporting and aggregation platform

## Summary

CivicSense is a full-stack decision-support system that helps municipal authorities process citizen-reported civic issues. When multiple citizens report the same pothole, garbage dump, or water leak, the platform identifies related reports using text semantic similarity and geospatial proximity, routes uncertain cases to human officers for review, and provides explainable priority scoring.

## Key Features

- **Duplicate Detection**: Text embedding similarity (MiniLM-L6-v2) combined with spatial proximity and category compatibility to identify related reports
- **Human-in-the-Loop Review**: Uncertain matches are presented to municipal officers with full evidence; no autonomous decisions
- **Explainable Priority Scoring**: 5-factor weighted formula (severity, volume, reporters, recency, persistence) with full breakdown
- **Audit Trail**: Every review decision is logged with reviewer identity, notes, and timestamps
- **Operational Dashboard**: React + TypeScript web interface for triage officers with real-time polling

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Alembic
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, TanStack Query
- **Mobile**: Kotlin + Jetpack Compose (Android), React Native + Expo (scaffold)
- **AI/ML**: sentence-transformers/all-MiniLM-L6-v2, PyTorch
- **Infrastructure**: Docker Compose, 555 automated tests (470 backend + 85 frontend)

## Architecture

- 29 REST API endpoints across 6 groups (Reports, Issues, Matches, Departments, AI, Health)
- 10 versioned database migrations
- 3-tier match routing: AUTO_LINK (≥0.70), CANDIDATE (0.45–0.70), NEW_ISSUE (<0.45)
- Synthetic pilot dataset: 40 reports, 12 issues, 10 candidate matches

## Status

Prototype / research system. Not production-ready. All evaluation metrics are on synthetic data.

## Links

- Repository: [github.com/your-org/civicsense](https://github.com/your-org/civicsense)
- Documentation: `docs/` directory
- API Docs: `http://localhost:8000/docs` (when running)
