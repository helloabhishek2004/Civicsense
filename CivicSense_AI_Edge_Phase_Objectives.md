# CivicSense — Edge AI & Multimodal Embedding Phase

> **Document type:** Phase objective and implementation guidance
> **Status:** Planning / model-validation phase
> **Scope:** Image-quality verification, mobile embedding generation, backend embedding validation, reference retrieval, and confidence-based decision support.
> **Related project:** CivicSense — From Citizen Reports to Civic Intelligence

---

## 1. Purpose of This Phase

This phase establishes the first practical AI pipeline for CivicSense. The goal is to introduce useful edge computing without prematurely building a large custom AI system or making the application dependent on a single model.

The intended architecture is:

```text
Citizen image + description
        ↓
On-device image-quality verification
        ↓
Retake / warning / continue
        ↓
On-device preprocessing
        ↓
MobileCLIP image + text embeddings
        ↓
Backend validation and storage
        ↓
Reference-embedding comparison
        ↓
Multimodal confidence and decision engine
        ↓
Automated provisional action or human review
```

This document is guidance for the coding/research agent. It is not a permanent rulebook. If a better, more reliable, or more practical approach is discovered, the agent may propose and adopt it after documenting the reason and updating this file.

The agent must also follow the broader protocols, architecture decisions, security practices, and conventions documented in the other project Markdown files.

---

## 2. Overall CivicSense Goal

CivicSense is not intended to be only an image classifier or complaint form. It is a hybrid edge-cloud, multimodal, human-in-the-loop civic decision-support platform.

The overall lifecycle is:

```text
EDGE → preprocess and represent submissions locally
  ↓
SERVER AI → compare and interpret multimodal evidence
  ↓
DECISION ENGINE → categorize, assess, rank, and route
  ↓
HUMAN → verify uncertain, sensitive, or high-impact cases
  ↓
CIVIC DATA → preserve verified reports and outcomes
  ↓
DATA MINING → discover hotspots, trends, and recurring problems
  ↓
AUTHORITY → manage and prioritize action
  ↓
FEEDBACK → capture corrections and resolutions
  ↓
MLOps → evaluate and improve the system
```

The current phase implements only the foundation of this lifecycle. It should not attempt to complete every AI or data-mining capability at once.

---

## 3. Main Objectives of This Phase

### Objective A — Establish a reliable image-quality gate

Before expensive embedding generation or upload, the mobile app should assess whether the image is usable for analysis.

The quality pipeline should identify:

- Corrupted or undecodable images
- Extremely low resolution
- Severe blur
- Extremely dark or overexposed images
- Very low contrast
- Obvious capture problems where practical

The output should not be limited to a binary result. Prefer three states:

```text
ACCEPT   → continue normally
WARNING  → inform the user; allow retake or controlled continuation
REJECT   → request a clearer image or another upload
```

Quality checks should provide understandable reasons, such as:

- “The image is too blurry.”
- “The image is too dark.”
- “The reported issue is too far away.”
- “The image resolution is too low.”

Do not use arbitrary thresholds without calibration. Thresholds must be tested using real images captured or collected for CivicSense.

### Objective B — Select and validate a mobile-compatible embedding model

The intended model family is **MobileCLIP**, subject to practical validation.

The model must be evaluated for:

- Image and text embedding compatibility
- Shared image-text semantic space
- Android deployment feasibility
- ONNX/TFLite/other runtime compatibility
- Model size
- RAM usage
- CPU/GPU performance
- Inference latency
- Quantization options
- License and redistribution conditions
- Accuracy degradation after conversion or quantization

Do not integrate a model into the Android app merely because its repository exists. First prove that the selected checkpoint works correctly and produces useful embeddings.

### Objective C — Generate compact multimodal representations on the device

The mobile pipeline should eventually generate:

- Image embedding
- Text embedding
- Image-quality metrics
- Model version
- Feature-pipeline version
- Basic preprocessing metadata

The device should also retain or upload a suitable compressed reference image and the original/normalized description for human review and auditing.

Embeddings are not a replacement for evidence. They are an additional machine-readable representation of the evidence.

### Objective D — Build backend embedding validation and storage

The backend must:

- Validate embedding dimensions
- Validate numeric values
- Reject NaN/infinite values
- Validate model and feature-pipeline versions
- Normalize vectors where required
- Store embeddings with report linkage
- Preserve image and text evidence
- Support reprocessing when models change
- Fall back to backend embedding generation when edge generation fails

The backend is authoritative. It must not blindly trust client-provided predictions, confidence scores, or quality scores.

### Objective E — Build a verified reference-embedding system

Incoming embeddings need meaningful reference points. The first version should use a small, curated, verified dataset rather than training a large custom model immediately.

Reference records should include:

- Image or image reference
- Description or text label
- Civic category
- Optional severity label
- Verification source/status
- Image embedding
- Text embedding, where applicable
- Embedding model version
- Dataset/reference version

Initial candidate categories may include:

1. Pothole
2. Road crack / surface damage
3. Water accumulation / drainage issue
4. Garbage / waste accumulation
5. Damaged civic infrastructure
6. Other / uncertain

The final category list must be based on dataset availability, practical separability, and project scope.

### Objective F — Implement multimodal similarity and decision support

The backend should compare incoming image and text embeddings with verified reference embeddings using methods such as:

- Cosine similarity
- Top-k nearest-neighbor retrieval
- Category-wise score aggregation
- Image/text agreement analysis

The initial decision engine may be implemented using deterministic logic. It should produce:

- Predicted category
- Similar reference examples
- Image similarity score
- Text similarity score
- Combined confidence
- Evidence agreement/conflict
- Human-review requirement
- Suggested department or workflow route

Do not force a category when similarity is weak. “Uncertain” is a valid and important output.

### Objective G — Add a safe fallback and human-review pathway

AI must assist the civic workflow, not become a single point of failure.

Reports should remain submit-able when:

- Mobile embedding generation fails
- The backend model is unavailable
- Vector search fails
- The image is unusual
- Image and text disagree
- Confidence is low
- Severity cannot be estimated reliably

Uncertain, conflicting, high-impact, or safety-sensitive cases should be routed to human review.

### Objective H — Prepare for future lightweight supervised learning

The first version does not need to train MobileCLIP or another large foundation model.

After verified reports accumulate, the project may train a small classifier on top of embeddings, such as:

- Logistic Regression
- Small MLP
- Another lightweight classifier justified by evaluation

This classifier should be treated as a later enhancement and must be compared against the simpler reference-similarity baseline.

---

## 4. Intended Technical Architecture

```text
┌───────────────────────────────────────────────┐
│                 Android App                   │
│                                               │
│ Capture/select image                          │
│ Enter description                             │
│ Basic image validation                        │
│ Blur/brightness/contrast checks               │
│ Image preprocessing                           │
│ Text preprocessing                            │
│                                               │
│ MobileCLIP image encoder                      │
│ MobileCLIP text encoder                       │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│                 Backend API                   │
│                                               │
│ Validate request and embeddings               │
│ Validate model/pipeline versions              │
│ Store report, evidence, and vectors           │
│ Backend embedding fallback                   │
└──────────────────────┬────────────────────────┘
                       │
             ┌─────────┴──────────┐
             ▼                    ▼
┌────────────────────┐  ┌───────────────────────┐
│ Reference Embedding│  │ Decision Engine        │
│ Store / Vector DB  │  │                       │
│                    │  │ Image/text similarity │
│ Verified examples  │  │ Score fusion           │
│ Category labels    │  │ Agreement/conflict     │
└─────────┬──────────┘  │ Confidence thresholds │
          │             │ Human-review routing  │
          └────────────▶└───────────┬───────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                  Provisional automation   Human review
                         │                     │
                         └──────────┬──────────┘
                                    ▼
                         Verified civic records
```

---

## 5. Model Strategy

### Primary model direction

Use **MobileCLIP** for image and text embeddings if the selected variant meets deployment and quality requirements.

The important property is that image and text embeddings must belong to a compatible shared semantic space. Arbitrary image and text embedding models must not be compared directly.

### Backend experimentation/fallback

A backend CLIP-compatible implementation, such as OpenCLIP or another compatible implementation, may be used for:

- Model evaluation
- Reference embedding generation
- Baseline experiments
- Backend fallback inference
- Comparison against the mobile-converted model

The exact backend model must be versioned and tested for compatibility with the mobile model. If the mobile and backend models produce incompatible vector spaces, the system must not compare their vectors as though they were interchangeable.

### Classification strategy

Initial version:

```text
Pretrained embedding model
        ↓
Reference-vector retrieval
        ↓
Own score fusion and decision logic
```

Later version, only after verified data is available:

```text
Embeddings + labeled metadata
        ↓
Lightweight trained classifier
        ↓
Calibrated category probabilities
```

Do not train a large model from scratch unless evaluation demonstrates that it is necessary and feasible.

### Severity strategy

Severity should initially be handled separately from category classification.

Possible initial inputs:

- Visual indicators
- Description keywords
- Road/public-space context
- Obstruction indicators
- Water accumulation
- Nearby report frequency
- Human reviewer input

Use a transparent rule-based score initially. A dedicated severity model can be considered later after collecting reliable severity labels.

---

## 6. Image-Quality Verification Guidance

### Mobile checks

The mobile app should perform inexpensive checks before embedding generation:

- Decode validity
- Minimum dimensions
- File size and format
- Blur estimate, such as Laplacian variance
- Brightness/exposure estimate
- Contrast estimate
- Orientation and basic image metadata

### Backend checks

The backend should repeat or validate important checks because the client is not trusted:

- Received file integrity
- Actual dimensions
- Blur and exposure metrics
- Image preprocessing consistency
- Optional issue-visibility checks

### Threshold policy

Thresholds must be empirical and configurable. Store the threshold/configuration version with the quality result.

Avoid one universal hard-coded quality number. Different conditions require different handling:

- Nighttime streetlight images may be dark but valid.
- A water-leakage image may contain reflective surfaces.
- A distant road issue may be useful despite low subject coverage.
- An urgent report may deserve submission with a warning rather than a hard block.

The quality system should distinguish between:

```text
Technically unusable
Potentially difficult to analyze
Usable for processing
```

---

## 7. Payload and Data Contract Direction

The exact API schema must follow the existing backend conventions, but the conceptual payload should contain:

```json
{
  "report_id": "client-generated-or-server-assigned-id",
  "description": "Large pothole near the junction",
  "image_reference": "compressed-review-image",
  "image_embedding": [],
  "text_embedding": [],
  "quality": {
    "status": "acceptable",
    "score": 0.0,
    "warnings": [],
    "pipeline_version": "edge-quality-v1"
  },
  "embedding": {
    "model_name": "mobileclip",
    "model_version": "mobileclip-variant-version",
    "dimension": 0,
    "generated_on": "device"
  },
  "metadata": {
    "latitude": 0.0,
    "longitude": 0.0,
    "timestamp": ""
  }
}
```

This is a conceptual contract, not a demand to copy the schema without checking the existing implementation.

The system should preserve:

- Original description
- Reviewable image
- Embeddings
- Quality metrics
- Model version
- Pipeline version
- Processing status
- AI output
- Human correction

---

## 8. Fallback Strategy

### Edge model failure

```text
MobileCLIP fails
    ↓
Submit image + description
    ↓
Backend generates embeddings
```

### Invalid edge vectors

```text
Invalid dimensions/values/version
    ↓
Discard client vectors
    ↓
Regenerate or mark processing pending
```

### Poor image quality

```text
Severe quality failure → request retake
Borderline quality → warn, allow retake or controlled continuation
```

### Low similarity

```text
No strong reference match
    ↓
Do not force a category
    ↓
Mark uncertain and route to human review
```

### Image/text conflict

```text
Image and text disagree
    ↓
Reduce confidence
    ↓
Require human review
```

### Backend/AI service outage

```text
Accept and persist report
    ↓
processing_status = pending
    ↓
Retry asynchronously
```

### Vector database failure

```text
Vector search unavailable
    ↓
Use an available backend inference path
    ↓
Otherwise queue for retry/human processing
```

### Severity uncertainty

```text
Severity uncertain
    ↓
Use unassessed/conservative status
    ↓
Human reviewer decides
```

### Core principle

> AI failure must affect processing status, not destroy or prevent preservation of a valid citizen report.

---

## 9. Evaluation Plan

Before calling this phase complete, evaluate the system at four levels.

### A. Image-quality evaluation

Create a small test set containing:

- Sharp images
- Blurry images
- Dark images
- Overexposed images
- Low-resolution images
- Distant subjects
- Nighttime civic images
- Realistic mobile-camera examples

Measure:

- False rejection rate
- False acceptance rate
- User-facing usefulness of feedback
- Processing time on the target device

### B. Embedding quality evaluation

Test whether semantically related images and descriptions are close in embedding space.

Questions to answer:

- Do pothole images retrieve pothole references?
- Do garbage images retrieve garbage references?
- Can the system separate road damage from water accumulation?
- Does text improve image-only predictions?
- How often do image and text disagree?
- How does quantization affect similarity quality?

### C. Mobile performance evaluation

Measure on the iQOO Neo 6 target device:

- Model load time
- Image preprocessing time
- Image embedding time
- Text embedding time
- Total processing time
- Peak RAM usage
- Battery/thermal behavior
- App responsiveness
- Failure rate

### D. Decision-system evaluation

Measure:

- Category accuracy or top-k retrieval accuracy
- Confidence calibration
- Uncertain-case detection
- Image/text conflict detection
- Human-review routing accuracy
- Duplicate/similar-report retrieval quality

Do not report only accuracy. For this project, false confidence and unsafe automation are equally important.

---

## 10. Definition of Done for This Phase

This phase is complete when the following are demonstrably working or documented:

- [ ] Image-quality checks run before embedding generation.
- [ ] Severe image-quality failures request a retake or replacement.
- [ ] Borderline images produce understandable warnings.
- [ ] Quality thresholds are configurable and tested with sample images.
- [ ] MobileCLIP variant is selected and its license is documented.
- [ ] MobileCLIP image and text encoders are validated.
- [ ] Mobile inference format/runtime is validated on the target device.
- [ ] Image and text embeddings are generated successfully.
- [ ] Embeddings include model and pipeline version metadata.
- [ ] Backend validates incoming vectors.
- [ ] Backend fallback embedding generation exists or is explicitly tracked as pending.
- [ ] Reference embeddings are generated from verified examples.
- [ ] Similarity search returns relevant reference examples.
- [ ] Image/text scores can be combined.
- [ ] Low-confidence and conflicting cases go to human review.
- [ ] Reports remain preserved when AI processing fails.
- [ ] Basic latency and quality evaluation results are recorded.
- [ ] Project documentation and progress notes are updated.

A feature should not be marked complete merely because code compiles. It must be tested against representative data and the target execution environment where applicable.

---

## 11. Suggested Implementation Order

1. Review existing Android, backend, database, and dashboard architecture.
2. Identify current report submission and processing contracts.
3. Create a small representative civic-image/text evaluation dataset.
4. Implement and calibrate basic image-quality checks.
5. Research and select the exact MobileCLIP checkpoint.
6. Validate MobileCLIP embeddings outside the Android app first.
7. Benchmark model size, latency, RAM, and compatibility.
8. Integrate mobile preprocessing and embedding generation.
9. Add backend vector validation and versioning.
10. Create reference embeddings from verified examples.
11. Implement similarity retrieval and score fusion.
12. Implement confidence thresholds and human-review routing.
13. Add backend fallback and asynchronous retry handling.
14. Evaluate the complete flow on the iQOO Neo 6.
15. Record results, limitations, and next-phase recommendations.

Do not skip model validation and benchmarking in order to reach UI integration faster. A smaller validated model is better than a theoretically powerful model that cannot run reliably on the target device.

---

## 12. Change Log / Progress Notes

Agents may update this section as the phase progresses. Keep entries concise and factual.

### 2026-09-12 — Initial phase definition

- Selected MobileCLIP as the intended edge image-text embedding direction.
- Defined image-quality verification as the first mobile AI stage.
- Defined backend reference-embedding comparison as the initial inference strategy.
- Chose human-in-the-loop handling for low-confidence, conflicting, high-impact, or uncertain reports.
- Deferred training a custom classifier until sufficient verified data is available.
- Defined backend embedding generation as the fallback when edge inference fails.

---

## 13. Open Questions to Resolve During Implementation

- Which exact MobileCLIP variant provides the best accuracy/performance trade-off?
- Can the selected checkpoint be exported reliably to the chosen Android runtime?
- Should image and text encoders run fully on-device, or should text processing remain lightweight initially?
- What minimum image quality is appropriate for each civic category?
- Which vector database best fits the existing backend and deployment constraints?
- Should reference embeddings be category centroids, individual examples, or both?
- What score-fusion weights produce the best validation results?
- How should severity be represented before enough labeled severity data exists?
- What confidence thresholds produce acceptable false-positive and false-negative behavior?
- Which reports must always require human verification?

Open questions should be resolved through experiments and documented decisions, not assumptions.

---

## 14. Guiding Principles

1. **Validate before integrating.**
2. **Prefer a small reliable model over a large impractical one.**
3. **Do not compare embeddings from incompatible spaces.**
4. **Keep original evidence alongside embeddings.**
5. **Treat client-generated AI outputs as untrusted input.**
6. **Never force a prediction when the evidence is weak.**
7. **Human review is a safety mechanism, not a failure of the system.**
8. **AI processing must be asynchronous and recoverable.**
9. **Version models, preprocessing, thresholds, and reference datasets.**
10. **Use human corrections as future evaluation and training data.**
11. **Keep the phase focused; avoid unnecessary foundation-model or cloud complexity.**
12. **Document better alternatives when they are discovered.**
