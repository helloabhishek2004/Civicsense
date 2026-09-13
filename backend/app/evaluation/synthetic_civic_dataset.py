"""Synthetic Civic Report Evaluation Dataset & Gold-Label Fixtures.

Provides a diverse, realistic, zero-PII synthetic dataset for evaluating:
1. Duplicate matching & issue aggregation (True duplicates, false duplicates, category conflicts)
2. Category classification across all canonical civic categories
3. Severity estimation consistency
4. Priority scoring across diverse defect profiles
5. Human-review routing and edge-case handling

All coordinates are located in the Bangalore metropolitan area with realistic synthetic offsets.
"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SyntheticReport:
    report_id: str
    text: str
    category: str
    latitude: float
    longitude: float
    expected_issue_group: str
    expected_severity: str
    notes: str


@dataclass(frozen=True)
class EvaluationPair:
    pair_id: str
    report_id_a: str
    report_id_b: str
    expected_relationship: str  # "SAME_ISSUE", "DIFFERENT_ISSUE", "UNCERTAIN"
    scenario_type: str  # TRUE_DUPLICATE, GEOGRAPHIC_SEPARATION, CATEGORY_MISMATCH, AMBIGUOUS
    notes: str


# ---------------------------------------------------------------------------
# 1. Synthetic Reports (24 structured cases)
# ---------------------------------------------------------------------------

SYNTHETIC_REPORTS: list[SyntheticReport] = [
    # --- Group A: True Duplicates - MG Road School Pothole (Cluster 1) ---
    SyntheticReport(
        report_id="SYN-REP-001",
        text="Large deep pothole near the school entrance on MG Road causing severe traffic jam.",
        category="Pothole",
        latitude=12.97160,
        longitude=77.59460,
        expected_issue_group="ISS-MG-POTHOLE",
        expected_severity="HIGH",
        notes="Primary anchor for MG Road school pothole cluster.",
    ),
    SyntheticReport(
        report_id="SYN-REP-002",
        text="Deep road hole outside the school gate on MG Road, vehicles swerving dangerously.",
        category="Pothole",
        latitude=12.97170,
        longitude=77.59468,  # ~14 meters from REP-001
        expected_issue_group="ISS-MG-POTHOLE",
        expected_severity="HIGH",
        notes="Same physical defect reported from slightly different vantage point outside gate.",
    ),
    SyntheticReport(
        report_id="SYN-REP-003",
        text="Pothole causing vehicles to slow down near the school entrance on MG Road.",
        category="Pothole",
        latitude=12.97155,
        longitude=77.59455,  # ~8 meters from REP-001
        expected_issue_group="ISS-MG-POTHOLE",
        expected_severity="MEDIUM",
        notes="Third report of the same school pothole with milder description.",
    ),

    # --- Group B: True Duplicates - City Market Garbage Dump (Cluster 2) ---
    SyntheticReport(
        report_id="SYN-REP-004",
        text="Huge pile of rotting garbage dumped near City Market East Gate, smelling terrible.",
        category="Garbage",
        latitude=12.96500,
        longitude=77.57500,
        expected_issue_group="ISS-MKT-GARBAGE",
        expected_severity="HIGH",
        notes="Anchor for City Market illegal waste dump.",
    ),
    SyntheticReport(
        report_id="SYN-REP-005",
        text="Trash overflowing onto pedestrian path outside City Market East Entrance.",
        category="Garbage",
        latitude=12.96508,
        longitude=77.57510,  # ~14 meters from REP-004
        expected_issue_group="ISS-MKT-GARBAGE",
        expected_severity="HIGH",
        notes="Duplicate report describing the same market waste overflow.",
    ),

    # --- Group C: True Duplicates - 4th Main Water Pipeline Burst (Cluster 3) ---
    SyntheticReport(
        report_id="SYN-REP-006",
        text="Water pipe broken and gushing drinking water continuously across 4th Main road.",
        category="Water Leakage",
        latitude=12.93500,
        longitude=77.61000,
        expected_issue_group="ISS-4TH-WATER",
        expected_severity="CRITICAL",
        notes="Major pipeline rupture flooding thoroughfare.",
    ),
    SyntheticReport(
        report_id="SYN-REP-007",
        text="Severe water leak flooding the entire road on 4th Main near the junction.",
        category="Water Leakage",
        latitude=12.93512,
        longitude=77.61015,  # ~21 meters from REP-006
        expected_issue_group="ISS-4TH-WATER",
        expected_severity="CRITICAL",
        notes="Duplicate citizen report for 4th Main water pipe flood.",
    ),

    # --- Group D: Related but Separate Issues (Different locations, same category) ---
    SyntheticReport(
        report_id="SYN-REP-008",
        text="Large pothole near 10th Cross Indiranagar damaging two-wheelers.",
        category="Pothole",
        latitude=12.97800,
        longitude=77.64000,
        expected_issue_group="ISS-INDIRA-POTHOLE-1",
        expected_severity="HIGH",
        notes="Pothole on 10th Cross Indiranagar (~5 km from MG Road).",
    ),
    SyntheticReport(
        report_id="SYN-REP-009",
        text="Deep pothole near 14th Cross Indiranagar outside bakery.",
        category="Pothole",
        latitude=12.97200,
        longitude=77.64800,  # ~1.1 km from REP-008
        expected_issue_group="ISS-INDIRA-POTHOLE-2",
        expected_severity="MEDIUM",
        notes="Separate pothole in the same suburb but distinct street/cross.",
    ),
    SyntheticReport(
        report_id="SYN-REP-010",
        text="Garbage piled up on Residency Road near bank ATM.",
        category="Garbage",
        latitude=12.97000,
        longitude=77.60000,
        expected_issue_group="ISS-RESIDENCY-GARBAGE",
        expected_severity="MEDIUM",
        notes="Garbage dump on Residency Road.",
    ),
    SyntheticReport(
        report_id="SYN-REP-011",
        text="Uncollected waste and trash on Brigade Road near cinema theater.",
        category="Garbage",
        latitude=12.97350,
        longitude=77.60750,  # ~900m from REP-010
        expected_issue_group="ISS-BRIGADE-GARBAGE",
        expected_severity="MEDIUM",
        notes="Separate waste accumulation on Brigade Road.",
    ),

    # --- Group E: Category Conflicts at Same Physical Location ---
    SyntheticReport(
        report_id="SYN-REP-012",
        text="Broken streetlight pole with sparking electrical wires at Central Park Main Gate.",
        category="Streetlight",
        latitude=12.98000,
        longitude=77.59000,
        expected_issue_group="ISS-CPARK-STREETLIGHT",
        expected_severity="CRITICAL",
        notes="Electrical hazard at Central Park Gate.",
    ),
    SyntheticReport(
        report_id="SYN-REP-013",
        text="Deep dangerous pothole right in front of Central Park Main Gate.",
        category="Pothole",
        latitude=12.98000,
        longitude=77.59000,  # Exactly 0 meters from REP-012
        expected_issue_group="ISS-CPARK-POTHOLE",
        expected_severity="HIGH",
        notes="Distinct road surface defect at identical coordinates to streetlight pole.",
    ),
    SyntheticReport(
        report_id="SYN-REP-014",
        text="Water leaking from underground valve at Central Park Main Gate.",
        category="Water Leakage",
        latitude=12.98005,
        longitude=77.59005,  # ~7 meters from REP-012/013
        expected_issue_group="ISS-CPARK-WATER",
        expected_severity="MEDIUM",
        notes="Third distinct municipal defect at Central Park Gate.",
    ),

    # --- Group F: Diverse Categories Across Civic Spectrum ---
    SyntheticReport(
        report_id="SYN-REP-015",
        text="Damaged sidewalk with missing paving slabs and exposed rebar on Church Street.",
        category="Road Damage",
        latitude=12.97450,
        longitude=77.60250,
        expected_issue_group="ISS-CHURCH-SIDEWALK",
        expected_severity="MEDIUM",
        notes="Pedestrian infrastructure defect.",
    ),
    SyntheticReport(
        report_id="SYN-REP-016",
        text="Large fallen tree branch blocking two lanes of traffic following thunderstorm.",
        category="Other",
        latitude=12.96800,
        longitude=77.59200,
        expected_issue_group="ISS-FALLEN-TREE",
        expected_severity="HIGH",
        notes="Obstruction falling under Other civic category.",
    ),
    SyntheticReport(
        report_id="SYN-REP-017",
        text="Open manhole on public footpath near elementary school, fatal hazard for kids.",
        category="Other",
        latitude=12.96200,
        longitude=77.58800,
        expected_issue_group="ISS-OPEN-MANHOLE",
        expected_severity="CRITICAL",
        notes="Extreme hazard requiring emergency priority.",
    ),
    SyntheticReport(
        report_id="SYN-REP-018",
        text="Traffic signal blackout at busy 4-way junction causing gridlock.",
        category="Streetlight",
        latitude=12.97500,
        longitude=77.61500,
        expected_issue_group="ISS-TRAFFIC-SIGNAL",
        expected_severity="HIGH",
        notes="Intersection traffic signal failure.",
    ),

    # --- Group G: Ambiguous, Vague & Edge-Case Reports ---
    SyntheticReport(
        report_id="SYN-REP-019",
        text="This is dangerous",
        category="Other",
        latitude=12.97162,
        longitude=77.59462,  # Close to MG Road pothole, but text completely uninformative
        expected_issue_group="ISS-UNCERTAIN-01",
        expected_severity="LOW",
        notes="Vague 3-word complaint. Insufficient semantic signal to merge safely.",
    ),
    SyntheticReport(
        report_id="SYN-REP-020",
        text="Bad road condition somewhere around here.",
        category="Road Damage",
        latitude=12.97165,
        longitude=77.59465,  # Close to MG Road pothole, general complaint
        expected_issue_group="ISS-UNCERTAIN-02",
        expected_severity="LOW",
        notes="Vague pavement complaint near specific pothole; candidate for human review.",
    ),
    SyntheticReport(
        report_id="SYN-REP-021",
        text="Large deep pothole near the school entrance on MG Road causing severe traffic jam.",
        category="Pothole",
        latitude=0.0,
        longitude=0.0,  # Null Island coordinates
        expected_issue_group="ISS-NULL-ISLAND-POTHOLE",
        expected_severity="HIGH",
        notes="Identical text to REP-001 but zero coordinates (Null Island GPS failure).",
    ),

    # --- Group H: Severity Variations ---
    SyntheticReport(
        report_id="SYN-REP-022",
        text="Small shallow depression in road surface on quiet residential cul-de-sac.",
        category="Pothole",
        latitude=12.92000,
        longitude=77.58000,
        expected_issue_group="ISS-QUIET-POTHOLE",
        expected_severity="LOW",
        notes="Low-severity pothole on low-traffic lane.",
    ),
    SyntheticReport(
        report_id="SYN-REP-023",
        text="Small amount of dry leaves and paper wrappers scattered near park bench.",
        category="Garbage",
        latitude=12.92100,
        longitude=77.58100,
        expected_issue_group="ISS-MINOR-LITTER",
        expected_severity="LOW",
        notes="Minor litter, non-hazardous, low severity.",
    ),
    SyntheticReport(
        report_id="SYN-REP-024",
        text="Continuous minor dripping from fire hydrant valve onto soft soil verge.",
        category="Water Leakage",
        latitude=12.92200,
        longitude=77.58200,
        expected_issue_group="ISS-MINOR-LEAK",
        expected_severity="LOW",
        notes="Low-severity minor leak not impacting roadway or property.",
    ),
]


# ---------------------------------------------------------------------------
# 2. Gold-Label Evaluation Pairs (20 representative test pairs)
# ---------------------------------------------------------------------------

EVALUATION_PAIRS: list[EvaluationPair] = [
    # --- True Duplicates (Same Issue, High Confidence) ---
    EvaluationPair(
        pair_id="PAIR-TD-01",
        report_id_a="SYN-REP-001",
        report_id_b="SYN-REP-002",
        expected_relationship="SAME_ISSUE",
        scenario_type="TRUE_DUPLICATE",
        notes="MG Road school pothole: identical category, ~14m distance, synonymous descriptions.",
    ),
    EvaluationPair(
        pair_id="PAIR-TD-02",
        report_id_a="SYN-REP-001",
        report_id_b="SYN-REP-003",
        expected_relationship="SAME_ISSUE",
        scenario_type="TRUE_DUPLICATE",
        notes="MG Road school pothole: identical category, ~8m distance, common wording.",
    ),
    EvaluationPair(
        pair_id="PAIR-TD-03",
        report_id_a="SYN-REP-004",
        report_id_b="SYN-REP-005",
        expected_relationship="SAME_ISSUE",
        scenario_type="TRUE_DUPLICATE",
        notes="City Market garbage: identical category, ~14m distance, overlapping vocabulary.",
    ),
    EvaluationPair(
        pair_id="PAIR-TD-04",
        report_id_a="SYN-REP-006",
        report_id_b="SYN-REP-007",
        expected_relationship="SAME_ISSUE",
        scenario_type="TRUE_DUPLICATE",
        notes="4th Main water pipe burst: identical category, ~21m distance, high urgency.",
    ),

    # --- Geographic Separation (Same Category, Distant Locations) ---
    EvaluationPair(
        pair_id="PAIR-GS-01",
        report_id_a="SYN-REP-001",
        report_id_b="SYN-REP-008",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="GEOGRAPHIC_SEPARATION",
        notes="MG Road Pothole vs Indiranagar Pothole: ~5 km apart. Must not merge.",
    ),
    EvaluationPair(
        pair_id="PAIR-GS-02",
        report_id_a="SYN-REP-008",
        report_id_b="SYN-REP-009",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="GEOGRAPHIC_SEPARATION",
        notes="Indiranagar 10th Cross vs 14th Cross: ~1.1 km apart. Must not merge.",
    ),
    EvaluationPair(
        pair_id="PAIR-GS-03",
        report_id_a="SYN-REP-004",
        report_id_b="SYN-REP-010",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="GEOGRAPHIC_SEPARATION",
        notes="City Market Garbage vs Residency Road Garbage: ~2.8 km apart.",
    ),
    EvaluationPair(
        pair_id="PAIR-GS-04",
        report_id_a="SYN-REP-010",
        report_id_b="SYN-REP-011",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="GEOGRAPHIC_SEPARATION",
        notes="Residency Road Garbage vs Brigade Road Garbage: ~900m apart.",
    ),

    # --- Category Incompatibility at Co-located Points (0-10m) ---
    EvaluationPair(
        pair_id="PAIR-CI-01",
        report_id_a="SYN-REP-012",
        report_id_b="SYN-REP-013",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="CATEGORY_MISMATCH",
        notes="Streetlight vs Pothole at Central Park Gate (0m distance). Incompatible categories.",
    ),
    EvaluationPair(
        pair_id="PAIR-CI-02",
        report_id_a="SYN-REP-012",
        report_id_b="SYN-REP-014",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="CATEGORY_MISMATCH",
        notes="Streetlight pole vs Water leak at Central Park Gate (~7m). Incompatible categories.",
    ),
    EvaluationPair(
        pair_id="PAIR-CI-03",
        report_id_a="SYN-REP-013",
        report_id_b="SYN-REP-014",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="CATEGORY_MISMATCH",
        notes="Pothole vs Water leak at Central Park Gate (~7m). Incompatible categories.",
    ),

    # --- Cross-Category Dissimilar Pairs (Far Apart) ---
    EvaluationPair(
        pair_id="PAIR-CD-01",
        report_id_a="SYN-REP-001",
        report_id_b="SYN-REP-004",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="CATEGORY_MISMATCH",
        notes="Pothole on MG Road vs Garbage at City Market (~2.3 km).",
    ),
    EvaluationPair(
        pair_id="PAIR-CD-02",
        report_id_a="SYN-REP-006",
        report_id_b="SYN-REP-015",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="CATEGORY_MISMATCH",
        notes="Water leakage on 4th Main vs Sidewalk damage on Church St (~4.5 km).",
    ),
    EvaluationPair(
        pair_id="PAIR-CD-03",
        report_id_a="SYN-REP-016",
        report_id_b="SYN-REP-017",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="CATEGORY_MISMATCH",
        notes="Fallen tree vs Open manhole: distinct defect types and ~800m apart.",
    ),

    # --- Ambiguous, Vague, and Coordinate-Edge Cases ---
    EvaluationPair(
        pair_id="PAIR-AM-01",
        report_id_a="SYN-REP-001",
        report_id_b="SYN-REP-019",
        expected_relationship="UNCERTAIN",
        scenario_type="AMBIGUOUS",
        notes="MG Road Pothole vs 'This is dangerous' (~3m). Vague text; defers to human review.",
    ),
    EvaluationPair(
        pair_id="PAIR-AM-02",
        report_id_a="SYN-REP-001",
        report_id_b="SYN-REP-020",
        expected_relationship="UNCERTAIN",
        scenario_type="AMBIGUOUS",
        notes="MG Road Pothole vs 'Bad road condition' (Road Damage, ~8m). Borderline candidate.",
    ),
    EvaluationPair(
        pair_id="PAIR-AM-03",
        report_id_a="SYN-REP-001",
        report_id_b="SYN-REP-021",
        expected_relationship="UNCERTAIN",
        scenario_type="AMBIGUOUS",
        notes="Identical text but REP-021 has (0, 0) Null Island coords. Missing location gating.",
    ),
    EvaluationPair(
        pair_id="PAIR-AM-04",
        report_id_a="SYN-REP-019",
        report_id_b="SYN-REP-020",
        expected_relationship="UNCERTAIN",
        scenario_type="AMBIGUOUS",
        notes="Two vague reports near each other without concrete defect descriptions.",
    ),

    # --- Severity Contrast / Low-Severity Cases ---
    EvaluationPair(
        pair_id="PAIR-SV-01",
        report_id_a="SYN-REP-022",
        report_id_b="SYN-REP-001",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="GEOGRAPHIC_SEPARATION",
        notes="Minor shallow cul-de-sac pothole vs arterial road crater (~6 km apart).",
    ),
    EvaluationPair(
        pair_id="PAIR-SV-02",
        report_id_a="SYN-REP-023",
        report_id_b="SYN-REP-004",
        expected_relationship="DIFFERENT_ISSUE",
        scenario_type="GEOGRAPHIC_SEPARATION",
        notes="Minor leaf litter vs commercial market dump (~5 km apart).",
    ),
]


def get_synthetic_reports() -> list[SyntheticReport]:
    """Return copy of all synthetic evaluation reports."""
    return list(SYNTHETIC_REPORTS)


def get_evaluation_pairs() -> list[EvaluationPair]:
    """Return copy of all gold-label evaluation pairs."""
    return list(EVALUATION_PAIRS)


def export_dataset_dict() -> dict[str, Any]:
    """Serialize the dataset into a standard dictionary for export."""
    return {
        "metadata": {
            "version": "1.0.0",
            "total_reports": len(SYNTHETIC_REPORTS),
            "total_pairs": len(EVALUATION_PAIRS),
            "unique_issue_groups": len(
                {r.expected_issue_group for r in SYNTHETIC_REPORTS}
            ),
            "duplicate_pairs": sum(
                1 for p in EVALUATION_PAIRS if p.expected_relationship == "SAME_ISSUE"
            ),
            "non_duplicate_pairs": sum(
                1 for p in EVALUATION_PAIRS if p.expected_relationship == "DIFFERENT_ISSUE"
            ),
            "uncertain_pairs": sum(
                1 for p in EVALUATION_PAIRS if p.expected_relationship == "UNCERTAIN"
            ),
        },
        "reports": [asdict(r) for r in SYNTHETIC_REPORTS],
        "pairs": [asdict(p) for p in EVALUATION_PAIRS],
    }
