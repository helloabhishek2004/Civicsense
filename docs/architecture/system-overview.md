# CivicSense — System Architecture Overview

**CivicSense — From Citizen Reports to Civic Intelligence** is a hybrid edge-cloud multimodal AI decision-support platform.

---

## 1. High-Level Architecture Flow

```text
Citizen Mobile App
        │
        ▼
Edge Processing (Image quality, resize, edge inference)
        │
        ▼
FastAPI Ingestion API
        │
        ▼
Report Storage & State Orchestration
        │
        ▼
Server AI Pipeline (Vision, Text, Fusion, Similarity)
        │
        ▼
Decision Engine (Category, Severity, Priority, Conflict Detection)
        │
        ├───► Human Verification Queue (for high uncertainty or critical severity)
        │            │
        │            ▼
        └────► Civic Database (Verified issues, reports, evidence, provenance)
                     │
                     ▼
             Data Mining Engine (Hotspots, Trends, Clusters, Frequent Patterns)
                     │
                     ▼
             Authority Dashboard (Priority queues, maps, analytics, lifecycle)
                     │
                     ▼
             Feedback Loop & MLOps (Retraining datasets, model evaluation)
```

---

## 2. Implementation Status Mapping

To ensure clarity for developers and AI agents, every component is classified as:
- **`IMPLEMENTED NOW`**: Built, tested, and runnable in the current bootstrap foundation.
- **`PLANNED`**: In scope for upcoming sprints; interfaces and contracts exist, but full models/algorithms are deferred.
- **`FUTURE`**: Post-MVP ideas and advanced integrations.

| Architecture Layer | Component | Status | Description in Initial Foundation |
| :--- | :--- | :--- | :--- |
| **Mobile** | React Native Expo Scaffolding | `IMPLEMENTED NOW` | Project structure, TypeScript strict mode, basic navigation, report screens. |
| **Mobile** | Typed API Client | `IMPLEMENTED NOW` | Handles requests, error formats, and request IDs. |
| **Mobile** | Edge Preprocessing & On-Device ML | `PLANNED` | Image normalization, quality score, lightweight local inference. |
| **Edge-Cloud Contract** | Shared Ingestion Schema | `IMPLEMENTED NOW` | JSON Schema specifying payload, location, metadata, and evidence refs. |
| **Backend API** | FastAPI Foundation | `IMPLEMENTED NOW` | Versioned routes (`/api/v1/health`, `/api/v1/reports`), middleware, error handling. |
| **Backend API** | Request ID & Logging | `IMPLEMENTED NOW` | `X-Request-ID` propagation, structured logging without sensitive data leaks. |
| **Domain Services** | Report Lifecycle Service | `IMPLEMENTED NOW` | Strict state machine managing 11 report lifecycle states. |
| **Domain Services** | AI Service Interfaces | `IMPLEMENTED NOW` | Explicit interfaces (`IVisionService`, `ITextService`, `IFusionService`, etc.) raising `NotImplementedError` (no fake AI). |
| **Data Layer** | PostgreSQL & SQLAlchemy 2.0 | `IMPLEMENTED NOW` | Models for `Report`, `Issue`, `Evidence`, `AIAnalysis`, `Verification`, `Resolution`, `ModelVersion`. |
| **Data Layer** | Alembic Migrations | `IMPLEMENTED NOW` | Initial schema migration establishing foreign keys and indices. |
| **Server AI** | Vision Pipeline (YOLO / classifier) | `PLANNED` | Server-side visual inference on raw images. |
| **Server AI** | Text Analytics (TF-IDF / embeddings)| `PLANNED` | Natural language contextual extraction and safety indicators. |
| **Server AI** | Multimodal Fusion | `PLANNED` | Agreement/conflict detection between image and text modalities. |
| **Server AI** | Similarity & Duplicate Detection | `PLANNED` | Vector similarity + geospatial/temporal constraint grouping. |
| **Decision Engine** | Severity & Priority Scoring | `PLANNED` | Multi-factor urgency calculation and human-review routing. |
| **Human Review** | Verification Queue & Workflow | `PLANNED` | Operational UI and workflow for human reviewers to confirm/adjust labels. |
| **Civic Intelligence**| Data Mining (Hotspots, Apriori) | `PLANNED` | Geospatial clustering, recurring problem detection, pattern mining. |
| **Authority** | Authority Dashboard | `PLANNED` | Web UI with interactive maps, priority queue, and lifecycle tracking. |
| **MLOps** | Model Registry & Feedback Retraining | `PLANNED` | Dataset collection from verified human feedback and automated retraining. |
| **External Systems**| Weather, Traffic, Municipal APIs | `FUTURE` | Third-party integrations for richer situational context. |

---

## 3. Core Architectural Distinctions

1. **`Report != Issue`**:
   - `Report` is an individual citizen submission.
   - `Issue` is a real-world civic problem on the ground.
   - Multiple reports map into a single issue group over time.
2. **`Confidence != Severity != Priority`**:
   - `Confidence`: Model's statistical certainty about the category.
   - `Severity`: Inherent physical risk or seriousness of the civic defect.
   - `Priority`: Action urgency based on severity, public impact, location, and report frequency.
3. **`Evidence != Embedding`**:
   - Original visual and textual evidence is preserved and securely referenceable.
   - Embeddings are lossy mathematical representations, not replacements for the original evidence.
4. **`Prediction != Decision`**:
   - AI outputs are raw evidence/probabilities; the Decision Engine applies business rules, threshold checks, and uncertainty bounds to determine whether automatic handling or human verification is warranted.
5. **Model Provenance**:
   - Every AI analysis record references the exact model version and preprocessing pipeline version that produced it.
