# CivicSense — Agent Operating Guidelines & Governance (AGENTS.md)

This file defines **HOW** AI agents and developers must operate within the CivicSense repository.
In contrast, [`memory.md`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/memory.md) records **WHAT** has actually been implemented.

> **Rule 0**: Do not confuse `AGENTS.md` with `memory.md`.
> - `AGENTS.md` is the operational playbook and governance constitution.
> - `memory.md` is the durable factual record of current implementation state.

---

## 1. Project Context

**CivicSense** is a civic issue reporting and intelligence platform designed to bridge citizen reports with municipal resolution workflows.

The planned system comprises:
- **Citizen Mobile Application**: React Native / Expo (strict TypeScript) for citizen issue reporting, image capture, and tracking.
- **Web-based Authority Dashboard**: Operational interface for municipal authorities, triage, human verification, and workflow management.
- **FastAPI Backend**: Python service providing REST endpoints, authentication, validation, orchestration, and business logic.
- **PostgreSQL Data Layer**: Relational data store (managed via SQLAlchemy 2.0 and Alembic) tracking reports, issues, evidence, AI outputs, and verifications.
- **AI/ML Processing Subsystem**:
  - Image and text analysis
  - Multimodal feature extraction and intelligence
  - Similarity, clustering, and related-report / duplicate detection
  - Severity assessment and priority recommendation
  - Human verification routing
  - Geospatial and historical defect analytics
  - MLOps-oriented model evaluation, feedback loops, and tracking

### Project Philosophy
While initiated in an academic setting, CivicSense adheres to **production-grade software engineering standards**:
- **Simplicity**: Favor straightforward, comprehensible solutions over convoluted designs.
- **Maintainability**: Clear separation of concerns, clean interfaces, and readable code.
- **Clear Architecture**: Strict boundaries between mobile, backend, dashboard, and ML modules.
- **Reliability & Reproducibility**: Repeatable migrations, consistent environments, deterministic runs.
- **Superior UX**: Accessible, clean, trustworthy, and responsive design.
- **Explainable AI Decisions**: Explicit confidence, severity, priority, and rationale—no opaque black boxes treated as infallible truth.
- **Lean Infrastructure**: Avoid premature infrastructure complexity (no unneeded distributed systems, queues, or microservices).

---

## 2. Memory File Rule (`memory.md`)

The repository root contains [`memory.md`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/memory.md).

### Pre-Task Requirement
Before beginning any implementation or refactoring task, the agent **MUST read `memory.md`**.
The agent must use `memory.md` to understand:
- Current architectural layout and component statuses
- Implemented features vs. planned placeholders
- Major technology choices and package constraints
- Existing AI/ML pipelines and service interfaces
- Major integrations and data contracts
- Historical architectural decisions and migrations
- Active system constraints and invariants

### Post-Task Evaluation
Upon task completion, the agent **MUST determine whether `memory.md` requires an update**.

#### Update `memory.md` when introducing or modifying:
- A major feature or user workflow
- A major subsystem or architectural layer
- A major API endpoint or data pipeline
- Database schema, models, or migration strategies
- An AI/ML model, pipeline, or scoring heuristic
- Edge or on-device processing capabilities
- External integrations or third-party service contracts
- An architectural decision record (ADR) or migration
- Replacement or deprecation of an important implementation
- Any meaningful change in core system behavior

#### DO NOT update `memory.md` for:
- Minor UI styling, color tweaks, spacing, or typography adjustments
- Small, isolated bug fixes
- Minor code refactoring or internal cleanup that preserves existing architecture
- Temporary scripts or throwaway experiments
- Routine test additions that do not alter architecture
- Fine-tuning parameters that do not alter the system pipeline

#### Maintenance Invariants
- When an implementation is replaced or superseded, **update or remove the obsolete entry**.
- **Never append contradictory information**; resolve conflicts immediately.
- `memory.md` represents the **CURRENT** repository state, not an append-only changelog.

---

## 3. General Agent Workflow

For every task, follow this strict 10-step sequence:

```
[1. Read AGENTS.md] ───────► [2. Read memory.md] ───────► [3. Inspect Relevant Files]
                                                                    │
[6. Make Changes] ◄───────── [5. Smallest Correct Path] ◄───────────┘
       │
       ▼
[7. Run Validation] ───────► [8. Check Regressions] ────► [9. Update memory.md (if worthy)]
                                                                    │
                                                                    ▼
                                                        [10. Provide Structured Summary]
```

1. **Read `AGENTS.md`**: Refresh operational rules and boundaries.
2. **Read `memory.md`**: Understand current implementation reality.
3. **Inspect Relevant Files**: Examine active code, configs, schemas, and tests.
4. **Understand Existing Patterns**: Reason about conventions and design before editing.
5. **Identify Smallest Correct Path**: Design minimal, robust changes satisfying requirements.
6. **Implement Changes**: Write clean, modular, and maintainable code.
7. **Run Validation**: Execute available linters, type checkers, tests, and builds.
8. **Review for Regressions**: Check adjacent callers, API contracts, and edge cases.
9. **Update `memory.md`**: If work meets the durability criteria, update the memory file.
10. **Provide Response**: Present a structured implementation summary.

*Never begin work by blindly generating new files or replacing functional architecture.*

---

## 4. Verification & Ground Truth ("Do Not Assume")

Never assume a feature is implemented because:
- It was discussed in chat or prompt instructions
- It appears in a future roadmap or backlog plan
- A `TODO` or placeholder exists in the code
- Another agent or documentation claimed it exists
- It is mentioned in `memory.md` but missing from the code
- A dependency is installed in `package.json` or `pyproject.toml`

**The actual code and repository configuration are the ultimate authority.**
If `memory.md` and the code disagree:
1. Inspect the code and active tests.
2. Treat the running repository state as authoritative.
3. Correct `memory.md` to reflect reality.

---

## 5. Architectural Principles

### 1. Prefer a Modular Monolith Initially
- Do not introduce microservices, distributed event buses (Kafka/RabbitMQ), Kubernetes, or external caching tiers unless explicitly justified and requested.
- Maintain internal modularity via clear package boundaries (e.g., `services/`, `repositories/`, `models/`, `api/`) before entertaining distributed services.

### 2. Avoid Premature Complexity
- Keep moving parts to an absolute minimum.
- Prioritize developer ergonomics: easy local execution, single-command development loops (`docker compose up`, `npm start`), and reproducible test runs.

### 3. Strict Separation of Concerns
Keep these domains distinct:
- **Presentation / UI**: Component rendering, visual state, user input.
- **API Communication**: HTTP clients, serialization, network errors.
- **Domain Logic**: Business rules, report status progression, validation logic.
- **Data Access**: Repositories, queries, ORM persistence.
- **AI/ML Inference**: Isolated inference wrappers, feature extraction.
- **Background Processing**: Asynchronous workers and tasks.
- **Storage**: Media and raw evidence blob persistence.
- **Authentication & Authorization**: Identity verification and role policies.

*Never embed business logic or database queries directly inside UI views or API route controllers.*

### 4. Clear Mobile, Backend, and Dashboard Boundaries
- **Mobile Client (Citizen)**:
  - Intuitive reporting interface, camera/media capture, and device metadata (GPS, timestamp).
  - Lightweight client-side input validation and local error handling.
  - Optional lightweight on-device inference (e.g., photo quality checks, blur detection).
  - Status display and report tracking.
- **FastAPI Backend (Central Intelligence & Orchestration)**:
  - Canonical validation, security, and payload parsing.
  - Relational persistence and evidence reference integrity.
  - Heavy AI/ML processing (vision, text analysis, embeddings, fusion).
  - Similarity clustering, duplicate matching, and issue linkage.
  - Severity calculation, priority assignment, and triage routing.
  - Workflow lifecycle management and audit logs.
- **Web Dashboard (Authority Workflows)**:
  - Municipal triage, spatial and tabular issue visualization.
  - Human review interface (verification of AI classification/duplicates).
  - Department assignment, SLA tracking, and resolution verification.
  - Historical trends, clustering, and analytics reporting.

*Do not push heavy backend or analytics tasks to the mobile client. Do not treat the web dashboard as an AI compute engine—it is an authority management portal.*

---

## 6. AI/ML Implementation Rules

### 1. Do Not Overclaim Model Capabilities
A machine learning output is a probabilistic estimation, never unquestioned ground truth.
Always decouple and distinguish:
- **Prediction**: What the model classified (e.g., "Pothole").
- **Confidence**: Model probability score (e.g., `0.84`).
- **Severity**: Physical impact/hazard level (e.g., `HIGH`).
- **Priority**: Operational dispatch urgency (e.g., `CRITICAL`).
- **Verification Status**: Human review confirmation (`CONFIRMED`, `CORRECTED`, `REJECTED`).

*Never present raw model inferences as verified facts in the UI or database.*

### 2. Preserve Raw Evidence
Embeddings, feature vectors, and classification tags are derived representations—they do **not** replace original evidence.
- Raw evidence (images, audio, original text) must be durably stored with tamper-evident hashes.
- Never discard original media because an embedding was computed.
- Maintain privacy-conscious access controls over stored evidence.

### 3. Explicit Edge vs. Server Boundaries
When on-device ML is introduced, thoroughly document:
- Exact model artifact, runtime (e.g., LiteRT / ONNX Runtime), and version.
- Quantization level, memory footprint, and latency profile.
- Explicit rationale for running on-device (e.g., instant offline feedback on blurriness).
- Clear fallback behavior if the device cannot execute the model.

*Do not deploy heavy neural nets, vector databases, or complex fusion pipelines to mobile clients.*

### 4. Baselines First, Complexity Second
- **Text Analysis**: Establish simple baselines (keyword matching, TF-IDF, linear models) before adopting transformer architectures.
- **Vision**: Establish working convolutional/standard vision baselines before custom composite architectures.
- **Multimodal Fusion**: Benchmark early unimodal baselines against multimodal fusion before claiming performance gains.

### 5. Empirical Evaluation Over Assumptions
Any modification to an AI/ML pipeline must be evaluated using standard metrics:
- Classification: Accuracy, Precision, Recall, Macro/Micro F1, Confusion Matrix.
- Spatial/Detection: IoU, mAP where applicable.
- Operational: Latency (p50, p95, p99), memory consumption, artifact size, compute cost.
- Explainability: Document why a decision was reached.

### 6. Explicit Uncertainty Handling
Never force inputs into false certainty. Support explicit uncertainty states:
- `UNKNOWN`: Insufficient signals to classify.
- `OTHER`: Valid civic issue outside supported taxonomy.
- `REVIEW_REQUIRED`: Low confidence or conflicting multimodal signals.
- `LOW_CONFIDENCE`: Score falls below operational threshold.
- `CONFLICTING_EVIDENCE`: Text and image modalities strongly disagree.

---

## 7. Code Quality & Engineering Standards

- **Clarity over Cleverness**: Write readable, predictable, and self-documenting code.
- **Focused Units**: Keep functions and classes focused on a single responsibility.
- **No Monolithic Files**: Split files logically when responsibilities diverge.
- **Defensive Programming**: Validate inputs early; fail fast with clear errors.
- **Purposeful Comments**: Explain *why* something is done when counter-intuitive; do not restate what code syntax does.
- **Linting & Formatting**: Adhere strictly to project tooling (e.g., `ruff`, `mypy` for Python; `eslint`, `prettier` for TypeScript).
- **Scope Discipline**: Do not modify unrelated files or reformat working modules outside the task scope.
- **Clean Production Paths**: Remove all debug statements (`console.log`, `print()`), temporary test hacks, and scratch artifacts before concluding.

---

## 8. Dependency Management Rules

Before introducing a new package or library:
1. Verify if existing project dependencies or standard libraries already satisfy the requirement.
2. Check package license (prefer MIT, Apache 2.0, BSD; avoid copyleft/restrictive licenses).
3. Evaluate dependency weight, maintenance velocity, and security footprint.
4. Never add multiple libraries that serve identical functions.
5. Provide clear justification when adding a major dependency:
   - What problem does it solve?
   - Where will it be used?
   - Why is the existing stack insufficient?
6. Avoid casual major version updates that risk breaking API contracts or runtime stability.

---

## 9. Database & Persistence Rules

- **Entity Distinction**: Maintain the core domain distinction between `Report` (citizen submission event) and `Issue` (deduplicated real-world defect entity).
- **Managed Migrations**: Schema alterations must be performed via versioned migration scripts (Alembic). Never alter database structures ad-hoc.
- **Data Integrity**: Enforce constraints, relationships, foreign keys, and indexes at the database level.
- **Idempotency & Reproducibility**: Ensure migrations run cleanly up and down.
- **Audit Trails**: Preserve history. Do not destructively overwrite or delete audit logs, verifications, or evidence.
- **Zero Secrets**: Never include database credentials, seed passwords, or private keys in source code or migration files.

---

## 10. API & Contract Standards

- **Strict Validation**: Validate all inbound payloads using declarative schemas (Pydantic v2 / Zod).
- **Versioned Endpoints**: Expose endpoints under clean version prefixes (e.g., `/api/v1/`).
- **Unified Error Responses**: Format all API errors uniformly:
  ```json
  {
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "The requested report does not exist.",
      "request_id": "req-123456",
      "details": []
    }
  }
  ```
- **Traceability**: Propagate `X-Request-ID` across middleware, logging, and error payloads.
- **Client Mistrust**: Never trust client-declared AI classifications, severity levels, or verification statuses without server-side validation.
- **No Leaked Internals**: Mask raw database exceptions, stack traces, and internal server paths in API responses.

---

## 11. Security, Privacy, and Data Governance

CivicSense handles citizen data, photos, descriptions, timestamps, and geographic coordinates.

- **Secrets Management**: Read credentials exclusively from environment variables (`.env`). Never commit credentials or API keys.
- **Location Privacy**: Store high-precision coordinates securely; avoid publishing unneeded precision to public feeds if sensitive.
- **Safe File Ingestion**:
  - Enforce maximum upload size limits.
  - Validate file signatures (magic bytes) alongside declared MIME types.
  - Sanitize filenames and generate isolated storage keys (e.g., UUID-based paths).
- **Sensitive Data in Logs**: Never write passwords, tokens, full citizen names, or raw image buffers to standard output or log streams.
- **Access Control**: Enforce explicit role-based access control (RBAC) separating citizens from municipal verification officers.
- **Synthetic Test Data**: Use realistic synthetic data or anonymized fixtures for local testing. Never use real personal data.

---

## 12. User Experience & Interface Standards

Interfaces (Mobile & Web Dashboard) must feel **professional, accessible, calm, and trustworthy**:
- **Visual Clarity**: Maintain strong visual hierarchy, legible typography, and WCAG-compliant color contrast.
- **State Feedback**: Provide distinct, polished states for loading, empty results, success, and errors.
- **Error Guidance**: Display actionable, human-friendly error messages rather than raw tech codes.
- **Mobile Ergonomics**: Ensure generous touch targets (minimum 48x48 dp), smooth transitions, and responsive layouts across screen sizes.
- **Restraint**: Avoid distracting animations, noisy gradients, or decorative clutter. Clarity and utility take precedence over flair.

---

## 13. Testing & Validation Expectations

Before marking a task complete, run the most stringent applicable validations:

| Domain | Validation Checks |
| :--- | :--- |
| **Backend** | `pytest`, `ruff check`, `mypy` |
| **Mobile** | `npm test`, `npm run lint`, TypeScript compilation (`npx tsc --noEmit`) |
| **Dashboard** | Web build check, unit tests, linting |
| **Database** | Migration check (`alembic upgrade head`), schema round-trip tests |
| **AI/ML** | Evaluation test scripts, metric sanity checks, pipeline contract tests |

- If a specific test suite cannot be run locally (e.g., missing hardware or external dependency), **state this explicitly**.
- Never claim code is operational without executing verification commands.

---

## 14. Documentation & Artifact Synchronization

- Maintain parity between code and documentation.
- Update relevant architecture diagrams, `README.md`, or API specs when introducing architectural changes.
- Avoid duplicate documentation: keep `memory.md` focused on architectural reality, and point other documents to their canonical sources.

---

## 15. Task Scope & Architectural Discipline

- **Respect Task Scope**: Implement the requested change cleanly without gratuitous refactoring or unsolicited feature additions.
- **Escalation Protocol**: If a requested task contradicts sound engineering principles, introduces security flaws, or incurs extreme technical debt:
  1. Briefly explain the trade-offs and risks.
  2. Propose a cleaner, safer alternative.
  3. Proceed with the agreed solution.

### Protocol for Major Architectural Changes
Before altering an architectural foundation:
1. Identify what is changing and why the current solution is inadequate.
2. Formulate the replacement strategy and map all impacted files and consumers.
3. Assess backward compatibility, data migration needs, and breaking changes.
4. Execute the migration cleanly.
5. Immediately update [`memory.md`](file:///c:/Users/abhis/OneDrive/Desktop/Civicsense/memory.md) and remove deprecated artifacts.

---

## 16. Standard Agent Response Format

Every completed task must conclude with this concise reporting structure:

```markdown
## Implementation Summary

### Changed
- Concise list of functional and structural changes made.

### Validation
- Specific commands, test suites, or manual verification flows executed.
- Note any tests that could not be run.

### Memory
- State whether `memory.md` was updated (Yes/No).
- If updated, summarize the durable architectural information added or modified.

### Notes
- Critical assumptions, known limitations, follow-up items, or pending risks.
```

---

## 17. Final Guiding Rule

> **Act as a disciplined senior engineer in a production codebase.**
> 
> - **Before changing anything**: Understand the current system and read `memory.md`.
> - **While changing anything**: Preserve architectural consistency and separation of concerns.
> - **After changing anything**: Verify rigorously and record durable architectural facts in `memory.md`.
> 
> *Do not optimize for writing the most code.*  
> *Optimize for delivering the smallest correct, maintainable, and reliable implementation.*
