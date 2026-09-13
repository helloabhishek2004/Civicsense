# CivicSense — ML Dataset Annotation Taxonomy & Guidelines (v1.0)

**Document Version:** 1.0.0  
**Effective Date:** 2026-09-13  
**Status:** Canonical Visual Annotation Standard  
**Governing Architecture:** MobileNetV3-Small (Primary) / EfficientNet-Lite0 (Backup) for Civic Edge & Server Triage

---

## 1. Purpose & Scope

This document establishes the canonical visual annotation standard for the CivicSense project. It governs the curation, labeling, quality filtering, and partition of training, validation, and benchmark datasets.

All human annotators, automated curation scripts, and quality audit routines must adhere strictly to these rules. In accordance with `AGENTS.md` and production ML engineering principles:
- **No false certainty**: Ambiguous or borderline images must never be forced into a canonical category.
- **Physical ground truth**: Annotations represent physical real-world defects observable in the imagery, distinct from municipal dispatch priority or bureaucratic department ownership.
- **Auditability**: Every sample record must retain complete provenance, verification level, and secondary tags.

---

## 2. Canonical Civic Categories & Visual Criteria

The CivicSense visual taxonomy comprises six mutually exclusive primary target classes, supplemented by explicit secondary tags and ambiguity statuses.

### 2.1 Pothole (`Pothole`)

* **Definition**: A localized cavity, depression, or void in a paved road, street, or highway asphalt/concrete surface, formed by wear, water infiltration, freeze-thaw cycles, or mechanical impact.
* **Positive Inclusion Criteria**:
  - Localized structural bowl-shaped or irregularly bounded cavity in the road surface.
  - Visible structural depth, depression below the surrounding road grade, or exposed underlying aggregate / road base.
  - Distinct perimeter edges clearly differentiating the depression from surrounding planar pavement.
* **Negative Exclusion Criteria**:
  - Longitudinal, transverse, or thermal surface cracks without pavement loss or cavity formation ($\to$ `Road Damage`).
  - Extensive alligator/fatigue cracking without a localized cavity ($\to$ `Road Damage`).
  - Surface oil, water, or chemical stains without structural pavement loss ($\to$ `Other` or `quarantine`).
  - Intentional roadway features: speed bumps, rumble strips, expansion joints, utility access plates, or manhole frames ($\to$ `Other` or `out_of_domain`).
* **Visual Boundary Nuance**:
  - *Pothole vs. Cracking*: If severe alligator cracking has crumbled and dislodged material creating a depression $\ge 3\text{ cm}$ deep with visible cavity walls, classify as `Pothole`. If the asphalt is fractured but retains planar alignment with minimal displacement, classify as `Road Damage`.

---

### 2.2 Road Damage (`Road Damage`)

* **Definition**: Structural deterioration or physical defect of a roadway, paved street, or public pedestrian sidewalk that does not constitute a discrete, localized pothole cavity.
* **Positive Inclusion Criteria**:
  - Longitudinal or transverse structural cracks in asphalt or concrete.
  - Alligator / fatigue cracking (interconnected polygonal crack patterns resembling reptile skin).
  - Surface raveling, severe stripping, crumbling asphalt edges, or washboarding.
  - Rutting, corrugation, or severe pavement heaving / subsidence along wheelpaths.
  - Sunken or improperly restored utility trench cuts causing continuous pavement dips.
  - Cracked, broken, lifted (e.g. tree root heaving), or dislodged concrete sidewalk slabs.
* **Negative Exclusion Criteria**:
  - Localized, defined cavity depression with exposed base ($\to$ `Pothole`).
  - Paint peeling or faded lane markings without physical pavement defect ($\to$ `Other`).
  - Dirt, gravel, or unpaved rural paths in their normal unpaved state ($\to$ `out_of_domain`).
  - Clean construction excavation sites with proper safety barriers and signage ($\to$ `out_of_domain`).
* **Visual Boundary Nuance**:
  - *Dominance over Pothole*: If an image depicts widespread road distress (e.g., 50 meters of alligator cracking) and a tiny 5 cm surface chip, `Road Damage` is the dominant civic issue. Conversely, if a single major 40 cm crater dominates the lane surrounded by incidental hairline cracks, `Pothole` takes dominance.

---

### 2.3 Garbage (`Garbage`)

* **Definition**: Solid municipal waste, refuse, discarded bulk items, litter, or overflowing debris accumulating in the public right-of-way, sidewalks, parks, or roadsides.
* **Positive Inclusion Criteria**:
  - Illegal dumping of bulk furniture, mattresses, construction debris, or tires on public land.
  - Overflowing municipal waste receptacles or dumpsters where trash spills onto the ground.
  - Loose scattered litter (bottles, cans, food wrappers, paper, plastic bags) concentrated along gutters or walkways.
  - Piles of uncollected household garbage bags left outside designated collection points or torn open.
* **Negative Exclusion Criteria**:
  - Standard municipal waste containers standing curbside on scheduled collection days in orderly condition ($\to$ `no_visible_issue`).
  - Neatly bundled garden clippings or leaves waiting for scheduled seasonal pickup ($\to$ `no_visible_issue` or `Other`).
  - Naturally occurring fallen autumn leaves or tree branches on lawns ($\to$ `out_of_domain` or `no_visible_issue`).
  - Commercial shipping pallets or building materials stored inside an active, permitted construction staging area ($\to$ `out_of_domain`).
* **Visual Boundary Nuance**:
  - *Garbage vs. Stored Materials*: If goods or materials are neatly stacked adjacent to a commercial establishment or private driveway without refuse character, do not label as `Garbage`. If items are broken, scattered, abandoned, or obstructing pedestrian pathways, label as `Garbage`.

---

### 2.4 Water Leakage (`Water Leakage`)

* **Definition**: Uncontrolled discharge, pooling, or flow of potable water, stormwater, or wastewater originating from damaged or malfunctioning municipal water infrastructure.
* **Positive Inclusion Criteria**:
  - Ruptured water main, broken pipe, or pressurized water jet erupting from street or sidewalk.
  - Leaking or sheared fire hydrant discharging water into the roadway.
  - Water bubbling up through pavement cracks, curb lines, or around manhole covers under pressure.
  - Sewage or wastewater overflow from municipal sewer lines, clogged storm drains, or backed-up manholes flooding public rights-of-way.
  - Localized flood pooling on a dry day directly traceable to an adjacent leaking infrastructure element.
* **Negative Exclusion Criteria**:
  - Normal rainwater accumulation, puddles, or wet roadway surfaces immediately following rainfall without evidence of an infrastructure source ($\to$ `no_visible_issue` or `quarantine`).
  - Natural bodies of water (rivers, canals, ponds, ocean shores, drainage creeks) in their natural banks ($\to$ `out_of_domain`).
  - Permitted municipal street washing or fire department training operations ($\to$ `out_of_domain`).
* **Sewage Overflow Policy**:
  - *Infrastructure Source*: Any sewage or wastewater overflow emanating from an open, blocked, or ruptured municipal pipe, sewer main, or manhole is classified as `Water Leakage`. It must be annotated with the secondary tag `"sewage_overflow"`.
  - *Dry / Dumped Sludge*: Solid septic waste or sludge dumped on dry ground without active liquid leakage is classified under `Garbage` (if dumped refuse) or `Other` (if biohazard/contamination).

---

### 2.5 Streetlight (`Streetlight`)

* **Definition**: Physical damage, structural failure, or electrical safety hazard affecting public street lighting poles, fixtures, luminaires, or associated municipal illumination standards.
* **Positive Inclusion Criteria**:
  - Knocked down, tilted, leaning, or vehicle-impacted streetlight pole.
  - Broken, shattered, dangling, or missing luminaire/lamp fixture atop the pole.
  - Exposed electrical wiring, missing base inspection/handhole cover plate, or dangling cables presenting public safety hazards.
  - Severe structural corrosion or rusting through the base of the lighting standard.
* **Negative Exclusion Criteria**:
  - Fully intact, operational streetlight pole with no physical defect visible in the image ($\to$ `no_visible_issue`). *Crucial Rule: Do NOT classify an image as `Streetlight` merely because a streetlight is visible in the background of a street photo.*
  - Traffic signal lights (red/yellow/green intersection traffic lights) mounted on dedicated traffic signal masts ($\to$ `Other`). *Exception: If a combined municipal utility pole carries both street lighting and a traffic head, and the lighting element is damaged, it is classified under `Streetlight`.*
  - Overhead private commercial neon signs, shopfront illumination, or decorative festival fairy lights ($\to$ `out_of_domain`).
  - Day/night operational status (e.g. lamp unlit at night): If daytime photo shows an intact pole with no visible damage, visual classification cannot infer bulb outage ($\to$ `no_visible_issue` or `ambiguous`).

---

### 2.6 Other (`Other`)

* **Definition**: A valid, physically visible municipal civic issue or defect on public property that falls outside the specific definitions of Potholes, Road Damage, Garbage, Water Leakage, and Streetlights.
* **Positive Inclusion Criteria**:
  - Illicit graffiti or vandalism on public municipal infrastructure, bridge abutments, or civic structures.
  - Damaged, bent, destroyed, or missing public traffic signs (e.g. Stop sign, Speed limit sign).
  - Broken, smashed, or missing public guardrails, median crash barriers, or pedestrian handrails.
  - Damaged public municipal park benches, bus shelters, or public playground equipment.
  - Fallen large tree limbs or uprooted municipal trees obstructing the public roadway or sidewalk (distinct from seasonal leaf drop).
  - Open, missing, or stolen utility manhole covers / storm grate covers presenting a direct pedestrian or vehicle hazard.
* **Negative Exclusion Criteria**:
  - Private property interior damage or residential building code violations outside public domain ($\to$ `out_of_domain`).
  - Blurry, unidentifiable, or corrupted imagery where no specific defect can be ascertained ($\to$ `quarantine` or `unusable`). *Rule: `Other` is an active civic defect category, NOT a dumping ground for low-quality or unrecognizable images.*
  - Routine urban scenes with zero defects ($\to$ `no_visible_issue`).

---

## 3. Boundary Resolution Matrix

| Candidate Visual Signal | Category A | Category B | Resolution Rule |
| :--- | :--- | :--- | :--- |
| Cavity in cracked asphalt | `Pothole` | `Road Damage` | If depression depth $\ge 3\text{ cm}$ with distinct perimeter edges $\implies$ **`Pothole`**. If shallow fracture without localized pit $\implies$ **`Road Damage`**. |
| Damaged pole at intersection | `Streetlight` | `Other` (Traffic Signal) | If primary fixture is a street illumination luminaire $\implies$ **`Streetlight`**. If primary fixture is a vehicular traffic signal control head $\implies$ **`Other`** (`traffic_signal`). |
| Street flooded with water | `Water Leakage` | `no_visible_issue` (Rain) | If originating from bubbling manhole, burst pipe, or broken hydrant $\implies$ **`Water Leakage`**. If standing rainwater after rainstorm with no leak source $\implies$ **`no_visible_issue`** / **`quarantine`**. |
| Trash in pothole | `Pothole` | `Garbage` | Apply Multi-Issue Dominance Policy (§4). Determine dominant hazard / defect. |
| Broken manhole cover | `Other` | `Road Damage` | Missing or displaced iron manhole cover $\implies$ **`Other`** (`manhole_hazard`). Crumbling asphalt surrounding an intact iron ring $\implies$ **`Road Damage`**. |

---

## 4. Multi-Issue Dominance & Secondary Tagging Policy

Images captured in urban environments frequently depict more than one municipal defect. Annotators and curation tools must follow this strict priority sequence:

```
[Determine Defect Dominance]
       │
       ├─► One issue is clearly the dominant reportable civic defect?
       │        ├── YES: Assign as primary_category; record remainder in secondary_categories.
       │        └── NO:  Evaluate physical hazard / dispatch severity.
       │
[Hazard / Severity Tie-Breaker]
       │
       ├─► Is one defect significantly more hazardous?
       │   (e.g., open cavity or live wire vs incidental surface litter)
       │        ├── YES: Dominant hazard becomes primary_category; record secondary_categories.
       │        └── NO:  Mark sample as ambiguity_status = "ambiguous".
       │
[Ambiguity Rule]
       │
       └─► Ambiguous samples must NEVER enter clean train or validation splits.
```

### Strict Dominance Invariants:
1. **Never assign by pixel area alone**: A large pile of loose leaves or background litter must not override an open, hazardous road pothole simply because it occupies more image pixels.
2. **First Criterion — Visual & Functional Dominance**: Identify the defect that constitutes the core subject and motivation for the civic report.
3. **Second Criterion — Safety Severity**: When visual dominance between two defects is comparable (e.g. a broken streetlight with exposed wire next to a broken sidewalk slab), the more severe physical safety hazard is selected as `primary_category`.
4. **Third Criterion — Ambiguity Flagging**: If no defensible single dominant defect can be justified, the record must be marked `ambiguity_status = "ambiguous"`, with all present issues listed in `secondary_categories`.
5. **Split Quarantine**: Any sample marked `ambiguous` is quarantined and prohibited from entering `train` or `validation` splits.

---

## 5. Ambiguity & Quarantine Status Taxonomy

Every dataset record must have an explicit `ambiguity_status` and `verification_status`.

| Status Code | Meaning | Training Split Eligibility |
| :--- | :--- | :--- |
| `clear` | Unambiguous single dominant civic defect conforming to taxonomy. | Eligible for `train` or `validation`. |
| `ambiguous` | Multiple co-equal defects, borderline visual cues, or disputed classification. | **Quarantined**; excluded from train/val. |
| `quarantine` | Severe defect in image quality, corrupted stream, or policy violation. | **Quarantined**; excluded from train/val. |
| `unusable` | Blank, black, pure noise, corrupted bytes, or unrecognizable content. | **Quarantined**; excluded from train/val. |
| `out_of_domain` | Non-civic subjects (e.g., indoor selfies, animals, pets, private rooms, food). | **Quarantined**; excluded from train/val. |
| `no_visible_issue` | Clean street, normal operating infrastructure, or scenery with zero defect. | Stored in inventory; excluded from defect training. |

---

## 6. Image Quality & Integrity Standards

Images are evaluated across five technical dimensions:

1. **File Format & Magic Bytes**: Must be decodable JPEG (`\xFF\xD8\xFF`), PNG (`\x89PNG\r\n\x1a\n`), or WebP (`RIFF....WEBP`).
2. **Dimension Constraints**: Width and height must be within $[64, 8192]$ pixels. Images outside these limits are rejected.
3. **Decompression Bomb Defense**: Total uncompressed pixel count must not exceed $25{,}000{,}000$ pixels.
4. **Extreme Aspect Ratio**: Aspect ratios exceeding $1:5$ or $5:1$ are flagged with `quality_flags = ["extreme_aspect_ratio"]` and reviewed.
5. **Blur & Low Resolution**:
   - *Low Resolution*: $\min(\text{width}, \text{height}) < 128\text{ px}$ is flagged as `is_low_res`.
   - *Blur*: Luminance gradient variance below threshold is flagged as `is_blurry`.
   - *Quality Acceptance Rule*: Low resolution or moderate blur does **NOT** automatically disqualify an image if the civic defect remains distinct and human-identifiable. Only unidentifiable blur triggers `unusable`.

---

## 7. Verification Methodology & Provenance

To maintain scientific integrity and prevent ground-truth contamination, every sample explicitly records how its label was validated:

* **`source_label`**: Label derived directly from upstream dataset metadata (e.g. Boston 311 CRM service request type). Source labels are treated as candidate ground truth, subject to automated quality and leakage checks.
* **`manual_review`**: Label verified or corrected through direct human visual inspection by a qualified reviewer.
* **`cross_verified`**: Label corroborated by multiple independent annotators or high-confidence multimodal agreement.

*Rule: Source labels must never be represented as manually verified without recorded human review metadata.*

---

## 8. Licensing & Ethical Governance

1. **Documented Open Provenance**: Every training sample must resolve to an authorized, documented open license (e.g., CC0, Public Domain, CC-BY, CC-BY-SA, ODC-PDDL, or ODbL) recorded at the image, record, or dataset level.
2. **Privacy Protection**: Images containing legible high-resolution close-ups of human faces or vehicle license plates must be blurred or quarantined prior to model training.
3. **Immutability of Evaluation Benchmark**: No training image or candidate sample may ever be derived from or duplicate any sample within `datasets/benchmark_v1/`.
