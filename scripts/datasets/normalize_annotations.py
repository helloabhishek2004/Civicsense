"""CivicSense Annotation Normalization Layer.

Maps external source dataset annotations into the canonical 6-category taxonomy:
- Pothole
- Road Damage
- Garbage
- Water Leakage
- Streetlight
- Other

Enforces strict outcome categories:
- ACCEPTED: Map to approved canonical category with explicit rationale.
- REJECTED: Out of domain, noisy, or irrelevant.
- MANUAL_REVIEW: Ambiguous label requiring human verification.
"""

import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# Ensure backend package is in sys.path when run as standalone script
repo_root = Path(__file__).resolve().parents[2]
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.ai.normalized_prediction import PredictionNormalizer  # noqa: E402


class MappingOutcome(str, Enum):
    """Categorical classification of normalization decision."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass
class NormalizedAnnotationRecord:
    """Normalized annotation output ready for benchmark ingestion."""

    source_dataset: str
    source_record_id: str
    original_category: str
    canonical_category: str | None
    outcome: MappingOutcome
    mapping_rationale: str
    original_annotation: dict[str, Any] = field(default_factory=dict)
    source_license: str = "unverified"
    license_url: str = ""
    attribution: str = ""
    source_url: str | None = None
    text_description: str | None = None
    bounding_boxes: list[dict[str, Any]] = field(default_factory=list)
    verification_level: str = "source_verified"
    visual_relevance: str = "direct_issue_visible"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["outcome"] = self.outcome.value
        return d


# Explicit mappings for RDD2022
RDD2022_MAPPINGS: dict[str, tuple[str | None, MappingOutcome, str]] = {
    "d40": ("Pothole", MappingOutcome.ACCEPTED, "Official RDD2022 pothole label"),
    "pothole": ("Pothole", MappingOutcome.ACCEPTED, "Explicit pothole string label"),
    "d20": (
        "Road Damage",
        MappingOutcome.ACCEPTED,
        "Alligator cracking indicating severe asphalt fatigue",
    ),
    "d00": ("Road Damage", MappingOutcome.ACCEPTED, "Longitudinal road surface crack"),
    "d10": ("Road Damage", MappingOutcome.ACCEPTED, "Transverse road surface crack"),
    "d43": (None, MappingOutcome.REJECTED, "Crosswalk paint blur; not structural road damage"),
    "d44": (None, MappingOutcome.REJECTED, "Lane line paint blur; not structural road damage"),
    "crack": ("Road Damage", MappingOutcome.ACCEPTED, "General road surface crack"),
}


def filter_taco_image_license(raw_license: str | None) -> tuple[bool, str]:
    """Strict per-image license filter for TACO dataset.

    Rules:
    - Explicitly acceptable open license (ODbL, verified CC-BY, CC0) -> eligible (True)
    - license=None / null -> excluded (False)
    - license="CC" without exact terms -> not automatically accepted (False)
    - Unknown license -> excluded (False)
    """
    if raw_license is None or str(raw_license).strip().lower() in ["", "none", "null"]:
        return False, "EXCLUDED_LICENSE_NULL: Image has no declared license in annotations.json"

    lic_clean = str(raw_license).strip()
    if lic_clean == "CC":
        return False, (
            "EXCLUDED_UNSPECIFIED_CC: Image license is unspecified 'CC' without exact terms"
        )

    lic_upper = lic_clean.upper()
    if "ODBL" in lic_upper or "OPENLITTERMAP" in lic_upper:
        return True, "ODC-ODbL-1.0 (OpenLitterMap & Contributors)"

    if any(k in lic_upper for k in ["CC-BY", "CC BY", "CC0", "PUBLIC DOMAIN"]):
        return True, lic_clean

    return False, f"EXCLUDED_UNKNOWN_LICENSE: Unverified license string '{lic_clean}'"


# Explicit mappings for TACO (Trash Annotations in Context)
TACO_GARBAGE_LABELS: set[str] = {
    "bottle", "plastic bottle", "glass bottle", "can", "drink can", "food can",
    "plastic bag", "bag", "litter", "garbage", "carton", "milk carton", "cup",
    "plastic cup", "disposable cup", "trash", "plastic wrapper", "wrapper",
    "cigarette", "cigarette butt", "straw", "plastic container", "container",
    "paper", "cardboard", "box", "debris", "styrofoam piece", "polystyrene",
    "aluminium foil", "foil", "canister", "aerosol", "broken glass",
}

# Explicit mappings for Boston 311 service request types
BOSTON311_MAPPINGS: dict[str, tuple[str | None, MappingOutcome, str]] = {
    # Pothole
    "request for pothole repair": (
        "Pothole",
        MappingOutcome.ACCEPTED,
        "Direct municipal pothole report",
    ),
    "pothole": ("Pothole", MappingOutcome.ACCEPTED, "Direct pothole report"),
    "potholes": ("Pothole", MappingOutcome.ACCEPTED, "Direct pothole report"),
    "pothole in street": ("Pothole", MappingOutcome.ACCEPTED, "Direct pothole report"),
    # Road Damage
    "road defect": ("Road Damage", MappingOutcome.ACCEPTED, "Structural roadway defect"),
    "roadway repair": ("Road Damage", MappingOutcome.ACCEPTED, "Roadway structural damage repair"),
    "sidewalk repair": ("Road Damage", MappingOutcome.ACCEPTED, "Damaged pedestrian walkway"),
    "sidewalk repair (make safe)": (
        "Road Damage",
        MappingOutcome.ACCEPTED,
        "Damaged pedestrian walkway repair",
    ),
    "street defect": ("Road Damage", MappingOutcome.ACCEPTED, "Roadway surface damage"),
    "sidewalk repair (safety issue)": (
        "Road Damage",
        MappingOutcome.ACCEPTED,
        "Hazardous sidewalk crack/break",
    ),
    "catchbasin": ("Road Damage", MappingOutcome.ACCEPTED, "Damaged catchbasin or road grate"),
    # Garbage
    "improper trash storage": ("Garbage", MappingOutcome.ACCEPTED, "Solid waste accumulation"),
    "improper storage of trash (barrels)": (
        "Garbage",
        MappingOutcome.ACCEPTED,
        "Improper storage of trash barrels",
    ),
    "illegal dumping": ("Garbage", MappingOutcome.ACCEPTED, "Illegal debris / waste dumping"),
    "trash": ("Garbage", MappingOutcome.ACCEPTED, "Uncollected litter or trash"),
    "overflowing trash": ("Garbage", MappingOutcome.ACCEPTED, "Public bin overflow / waste pile"),
    "litter": ("Garbage", MappingOutcome.ACCEPTED, "Street litter accumulation"),
    "empty litter basket": ("Garbage", MappingOutcome.ACCEPTED, "Public litter basket emptying"),
    "ce collection": ("Garbage", MappingOutcome.ACCEPTED, "Code enforcement waste collection"),
    "missed trash/recycling/yard waste/bulk item": (
        "Garbage",
        MappingOutcome.ACCEPTED,
        "Missed municipal waste collection",
    ),
    "overflowing or un-kept dumpster": (
        "Garbage",
        MappingOutcome.ACCEPTED,
        "Overflowing commercial dumpster",
    ),
    "trash on vacant lot": ("Garbage", MappingOutcome.ACCEPTED, "Solid waste accumulation on lot"),
    # Water Leakage
    "broken water main": (
        "Water Leakage",
        MappingOutcome.ACCEPTED,
        "Major pipe rupture / continuous water leak",
    ),
    "water leak": ("Water Leakage", MappingOutcome.ACCEPTED, "Continuous surface water leak"),
    "hydrant leak": ("Water Leakage", MappingOutcome.ACCEPTED, "Damaged leaking fire hydrant"),
    "leaking hydrant": ("Water Leakage", MappingOutcome.ACCEPTED, "Leaking municipal hydrant"),
    "street flood": (
        "Water Leakage",
        MappingOutcome.ACCEPTED,
        "Standing water from drainage/pipe defect",
    ),
    # Streetlight
    "street light outage": (
        "Streetlight",
        MappingOutcome.ACCEPTED,
        "Unlit or dead street luminaire",
    ),
    "streetlight knocked down": (
        "Streetlight",
        MappingOutcome.ACCEPTED,
        "Physically damaged or toppled streetlight pole",
    ),
    "street light out": ("Streetlight", MappingOutcome.ACCEPTED, "Inoperative streetlight"),
    "street light fixture": (
        "Streetlight",
        MappingOutcome.ACCEPTED,
        "Damaged streetlight fixture/wiring",
    ),
    "parks lighting/electrical issues": (
        "Streetlight",
        MappingOutcome.ACCEPTED,
        "Park and street luminaire electrical defects",
    ),
    "traffic signal repair": (
        "Streetlight",
        MappingOutcome.ACCEPTED,
        "Traffic signal and luminaire repair",
    ),
    # Other
    "sign defect": (
        "Other",
        MappingOutcome.ACCEPTED,
        "Traffic / civic sign damage outside top 5 categories",
    ),
    "graffiti": (
        "Other",
        MappingOutcome.ACCEPTED,
        "Public vandalism outside primary infrastructure categories",
    ),
    "graffiti removal": ("Other", MappingOutcome.ACCEPTED, "Graffiti vandalism removal"),
    "pwd graffiti": ("Other", MappingOutcome.ACCEPTED, "Public Works graffiti removal"),
    "tree maintenance": ("Other", MappingOutcome.ACCEPTED, "Urban foliage defect"),
    "poor conditions of property": (
        "Other",
        MappingOutcome.ACCEPTED,
        "Property condition defects outside primary categories",
    ),
    "abandoned vehicles": (
        "Other",
        MappingOutcome.ACCEPTED,
        "Abandoned vehicle on public way",
    ),
    "unshoveled sidewalk": (
        "Other",
        MappingOutcome.ACCEPTED,
        "Snow obstruction on pedestrian walkway",
    ),
    # Explicitly Rejected Categories
    "mice infestation - residential": (
        None,
        MappingOutcome.REJECTED,
        "Biological pest complaint; not civic physical infrastructure",
    ),
    "rodent activity": (
        None,
        MappingOutcome.REJECTED,
        "Biological pest complaint; not civic physical infrastructure",
    ),
    "contractor complaints": (
        None,
        MappingOutcome.REJECTED,
        "Contractual / administrative complaint",
    ),
    "work w/out permit": (
        None,
        MappingOutcome.REJECTED,
        "Zoning and building permitting enforcement",
    ),
    "parking enforcement": (
        None,
        MappingOutcome.REJECTED,
        "Traffic parking violation enforcement",
    ),
    # Manual Review / Ambiguous
    "equipment repair": (
        None,
        MappingOutcome.MANUAL_REVIEW,
        "Ambiguous equipment repair requiring context",
    ),
    "public works general request": (
        None,
        MappingOutcome.MANUAL_REVIEW,
        "General request requiring text review",
    ),
    "general request": (
        None,
        MappingOutcome.MANUAL_REVIEW,
        "Ambiguous request title without category context",
    ),
    "unspecified inquiry": (
        None,
        MappingOutcome.MANUAL_REVIEW,
        "Generic inquiry without civic defect category",
    ),
    "mayor's 24 hour hotline": (
        None,
        MappingOutcome.MANUAL_REVIEW,
        "General intake channel requiring text inspection",
    ),
}


def normalize_annotation(
    source_dataset: str,
    source_record_id: str,
    original_category: str,
    original_annotation: dict[str, Any] | None = None,
    text_description: str | None = None,
    bounding_boxes: list[dict[str, Any]] | None = None,
    source_license: str = "unverified",
    license_url: str = "",
    attribution: str = "",
    source_url: str | None = None,
    verification_level: str = "source_verified",
    visual_relevance: str = "direct_issue_visible",
) -> NormalizedAnnotationRecord:
    """Normalize a raw annotation from a supported source dataset."""
    src = source_dataset.lower().strip()
    norm_cat = original_category.strip().lower()
    raw_annotation = original_annotation or {}
    bboxes = bounding_boxes or []

    canonical_classes = set(PredictionNormalizer.CATEGORY_LABELS.keys())

    # 1. RDD2022
    if src == "rdd2022":
        if norm_cat in RDD2022_MAPPINGS:
            mapped_cat, outcome, rationale = RDD2022_MAPPINGS[norm_cat]
        else:
            mapped_cat, outcome, rationale = (
                None,
                MappingOutcome.REJECTED,
                f"Unknown RDD2022 label '{original_category}'",
            )

    # 2. TACO (with strict per-image license filter)
    elif src == "taco":
        litter_tokens = [
            "plastic", "can", "bottle", "paper", "waste",
            "trash", "litter", "cup", "wrapper",
        ]
        if norm_cat in TACO_GARBAGE_LABELS or any(item in norm_cat for item in litter_tokens):
            if source_license and source_license != "unverified":
                is_lic_ok, lic_rat = filter_taco_image_license(source_license)
                if is_lic_ok:
                    mapped_cat, outcome, rationale = (
                        "Garbage",
                        MappingOutcome.ACCEPTED,
                        f"TACO litter object '{original_category}' mapped to Garbage ({lic_rat})",
                    )
                    source_license = lic_rat
                else:
                    mapped_cat, outcome, rationale = (
                        None,
                        MappingOutcome.MANUAL_REVIEW,
                        f"TACO license not cleared: {lic_rat}",
                    )
            else:
                mapped_cat, outcome, rationale = (
                    "Garbage",
                    MappingOutcome.ACCEPTED,
                    f"TACO litter object '{original_category}' mapped to Garbage",
                )
        elif norm_cat in {"unlabeled", "background", "ambient"}:
            mapped_cat, outcome, rationale = (
                None,
                MappingOutcome.REJECTED,
                f"Non-object or background label '{original_category}'",
            )
        else:
            mapped_cat, outcome, rationale = (
                None,
                MappingOutcome.MANUAL_REVIEW,
                f"Unclassified TACO label '{original_category}' requires inspection",
            )

    # 3. Boston 311
    elif src == "boston311":
        if norm_cat in BOSTON311_MAPPINGS:
            mapped_cat, outcome, rationale = BOSTON311_MAPPINGS[norm_cat]
        else:
            matched = False
            for key, (m_cat, m_out, m_rat) in BOSTON311_MAPPINGS.items():
                if key in norm_cat:
                    mapped_cat, outcome, rationale = m_cat, m_out, f"Substring match: {m_rat}"
                    matched = True
                    break
            if not matched:
                mapped_cat, outcome, rationale = (
                    None,
                    MappingOutcome.MANUAL_REVIEW,
                    f"Unmapped Boston 311 category '{original_category}'",
                )

    # 4. Wikimedia / Geograph Water Leakage
    elif src in ["wikimedia_water", "commons_water"]:
        water_leak_terms = [
            "burst", "leak", "pipe", "main", "rupture", "water main",
            "conduite d'eau", "canonada", "overflow", "flooding", "water pipe",
        ]
        is_water = any(t in norm_cat for t in water_leak_terms) or any(
            t in (text_description or "").lower() for t in water_leak_terms
        )
        if is_water:
            lic_upper = (source_license or "").upper()
            is_valid_lic = any(k in lic_upper for k in ["CC", "PUBLIC DOMAIN", "PD", "ODC"])
            if is_valid_lic:
                mapped_cat = "Water Leakage"
                outcome = MappingOutcome.ACCEPTED
                rationale = "Verified infrastructure water pipe burst / leakage event"
            else:
                mapped_cat = None
                outcome = MappingOutcome.MANUAL_REVIEW
                rationale = f"Unverified license for water leakage: '{source_license}'"
        else:
            mapped_cat = None
            outcome = MappingOutcome.REJECTED
            rationale = f"Image label '{original_category}' does not indicate water pipe leakage"

    # 5. Wikimedia Municipal Street Lighting
    elif src in ["wikimedia_streetlight", "commons_streetlight"]:
        light_terms = [
            "street light", "streetlight", "lamp post", "lamppost",
            "street lamp", "light pole", "luminaire", "lighting", "lantern",
        ]
        is_light = any(t in norm_cat for t in light_terms) or any(
            t in (text_description or "").lower() for t in light_terms
        )
        if is_light:
            lic_upper = (source_license or "").upper()
            is_valid_lic = any(k in lic_upper for k in ["CC", "PUBLIC DOMAIN", "PD", "ODC"])
            if is_valid_lic:
                mapped_cat = "Streetlight"
                outcome = MappingOutcome.ACCEPTED
                rationale = "Verified municipal street lamp / lighting post infrastructure"
            else:
                mapped_cat = None
                outcome = MappingOutcome.MANUAL_REVIEW
                rationale = f"Unverified license for streetlight: '{source_license}'"
        else:
            mapped_cat = None
            outcome = MappingOutcome.REJECTED
            rationale = f"Image label '{original_category}' does not indicate street lighting"

    # 6. Wikimedia Road Damage / Cracks
    elif src in ["wikimedia_road_damage", "commons_road_damage"]:
        road_damage_terms = [
            "crack", "alligator", "asphalt", "pavement", "deterioration",
            "fissure", "road damage", "damaged road", "settlement", "roadway",
        ]
        is_road = any(t in norm_cat for t in road_damage_terms) or any(
            t in (text_description or "").lower() for t in road_damage_terms
        )
        if is_road:
            lic_upper = (source_license or "").upper()
            is_valid_lic = any(k in lic_upper for k in ["CC", "PUBLIC DOMAIN", "PD", "ODC"])
            if is_valid_lic:
                mapped_cat = "Road Damage"
                outcome = MappingOutcome.ACCEPTED
                rationale = "Verified roadway surface crack / asphalt damage defect"
            else:
                mapped_cat = None
                outcome = MappingOutcome.MANUAL_REVIEW
                rationale = f"Unverified license for road damage: '{source_license}'"
        else:
            mapped_cat = None
            outcome = MappingOutcome.REJECTED
            rationale = f"Image label '{original_category}' does not indicate road damage"

    # 7. Generic Wikimedia fallback
    elif src in ["wikimedia", "commons"]:
        lic_upper = (source_license or "").upper()
        is_valid_lic = any(k in lic_upper for k in ["CC", "PUBLIC DOMAIN", "PD", "ODC"])
        if not is_valid_lic:
            mapped_cat = None
            outcome = MappingOutcome.MANUAL_REVIEW
            rationale = f"Unverified license: '{source_license}'"
        elif any(t in norm_cat for t in ["water", "burst", "leak", "pipe"]):
            mapped_cat, outcome, rationale = (
                "Water Leakage",
                MappingOutcome.ACCEPTED,
                "Wikimedia water leakage event",
            )
        elif any(t in norm_cat for t in ["light", "lamp"]):
            mapped_cat, outcome, rationale = (
                "Streetlight",
                MappingOutcome.ACCEPTED,
                "Wikimedia street lighting infrastructure",
            )
        elif any(t in norm_cat for t in ["crack", "pavement", "asphalt", "road"]):
            mapped_cat, outcome, rationale = (
                "Road Damage",
                MappingOutcome.ACCEPTED,
                "Wikimedia roadway surface damage",
            )
        else:
            mapped_cat = None
            outcome = MappingOutcome.MANUAL_REVIEW
            rationale = f"Unclassified Wikimedia category '{original_category}'"

    # 8. Unknown source
    else:
        mapped_cat, outcome, rationale = (
            None,
            MappingOutcome.REJECTED,
            f"Unregistered source dataset '{source_dataset}'",
        )

    # Validate that accepted category is in canonical taxonomy
    if outcome == MappingOutcome.ACCEPTED:
        if mapped_cat not in canonical_classes:
            outcome = MappingOutcome.REJECTED
            rationale = (
                f"Mapped category '{mapped_cat}' is not in "
                f"authoritative taxonomy {canonical_classes}"
            )
            mapped_cat = None

    return NormalizedAnnotationRecord(
        source_dataset=source_dataset,
        source_record_id=source_record_id,
        original_category=original_category,
        canonical_category=mapped_cat,
        outcome=outcome,
        mapping_rationale=rationale,
        original_annotation=raw_annotation,
        source_license=source_license,
        license_url=license_url,
        attribution=attribution,
        source_url=source_url,
        text_description=text_description,
        bounding_boxes=bboxes,
        verification_level=verification_level,
        visual_relevance=visual_relevance,
    )
