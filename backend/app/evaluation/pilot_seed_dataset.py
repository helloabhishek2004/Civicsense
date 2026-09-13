"""Synthetic Pilot Dataset Generator for CivicSense Controlled Demonstration.

Provides 40 realistic synthetic citizen reports and 12 defect clusters (issues)
demonstrating all operational triage regimes without real citizen PII.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy.orm import Session


@dataclass
class PilotReportSpec:
    report_id: str
    tracking_id: str
    title: str
    description: str
    category: str
    severity: str
    latitude: float
    longitude: float
    address: str
    citizen_name: str
    citizen_phone: str
    citizen_email: str
    citizen_postal_code: str
    evidence_urls: list[str]
    days_ago: float
    status: str
    issue_code: str | None  # reference key to PilotIssueSpec or None if unlinked


@dataclass
class PilotIssueSpec:
    issue_code: str
    title: str
    category: str
    status: str  # OPEN, RESOLVED, CLOSED
    primary_latitude: float
    primary_longitude: float
    expected_priority_level: str
    notes: str


@dataclass
class PilotMatchSpec:
    match_code: str
    report_tracking_id: str
    candidate_issue_code: str
    action: str  # CANDIDATE, AUTO_LINK, NEW_ISSUE
    status: str  # PENDING, APPROVED, REJECTED, SUPERSEDED
    combined_score: float
    text_similarity: float
    distance_meters: float
    category_match: float
    reasoning: list[str]
    reviewer_id: str | None
    review_notes: str | None


# ---------------------------------------------------------------------------
# 1. 12 Defect Clusters (Issues)
# ---------------------------------------------------------------------------

PILOT_ISSUES: list[PilotIssueSpec] = [
    # Issue 1: High-Priority Crowded Arterial Pothole Cluster (8 reports)
    PilotIssueSpec(
        issue_code="ISS-MG-POTHOLE",
        title="Severe Deep Pothole Cluster near School on MG Road",
        category="Pothole",
        status="OPEN",
        primary_latitude=12.97160,
        primary_longitude=77.59460,
        expected_priority_level="CRITICAL",
        notes="Crowded issue with 8 reports, multiple citizen reporters, high traffic.",
    ),
    # Issue 2: Severe Single Emergency Defect (1 critical report)
    PilotIssueSpec(
        issue_code="ISS-OPEN-MANHOLE-RESIDENCY",
        title="Uncovered Deep Manhole on Main Pedestrian Crosswalk",
        category="Open Manhole",
        status="OPEN",
        primary_latitude=12.97250,
        primary_longitude=77.60100,
        expected_priority_level="CRITICAL",
        notes="High-severity single hazard report requiring immediate dispatch.",
    ),
    # Issue 3: High-Volume Commercial Garbage Dumping (5 reports)
    PilotIssueSpec(
        issue_code="ISS-MARKET-GARBAGE",
        title="Overflowing Commercial Garbage Dump at City Market Entry",
        category="Garbage",
        status="OPEN",
        primary_latitude=12.96020,
        primary_longitude=77.57440,
        expected_priority_level="HIGH",
        notes="Persistent waste accumulation over multiple days.",
    ),
    # Issue 4: Severe Municipal Main Water Line Burst (4 reports)
    PilotIssueSpec(
        issue_code="ISS-WATER-BURST-JAYANAGAR",
        title="Pressurized Main Water Pipe Rupture on 4th Main Road",
        category="Water Leakage",
        status="OPEN",
        primary_latitude=12.92980,
        primary_longitude=77.58320,
        expected_priority_level="HIGH",
        notes="Active potable water flooding roadway.",
    ),
    # Issue 5: Broken Streetlight Corridor (3 reports)
    PilotIssueSpec(
        issue_code="ISS-STREETLIGHT-INDIRANAGAR",
        title="Non-functioning Streetlights on 100ft Road Corridor",
        category="Broken Streetlight",
        status="OPEN",
        primary_latitude=12.97840,
        primary_longitude=77.64080,
        expected_priority_level="MEDIUM",
        notes="Corridor dark at night; safety concern.",
    ),
    # Issue 6: Damaged Footpath / Pavement Slabs (2 reports)
    PilotIssueSpec(
        issue_code="ISS-FOOTPATH-BRIGADE",
        title="Broken Concrete Pavers and Trip Hazard on Brigade Road",
        category="Damaged Footpath",
        status="OPEN",
        primary_latitude=12.97390,
        primary_longitude=77.60750,
        expected_priority_level="MEDIUM",
        notes="Pedestrian sidewalk deterioration.",
    ),
    # Issue 7: Fallen Tree Blocking Secondary Street (2 reports)
    PilotIssueSpec(
        issue_code="ISS-TREE-KORAMANGALA",
        title="Uprooted Gulmohar Tree Blocking 5th Block Transit Lane",
        category="Fallen Tree",
        status="OPEN",
        primary_latitude=12.93520,
        primary_longitude=77.62450,
        expected_priority_level="HIGH",
        notes="Partial road obstruction after heavy rain.",
    ),
    # Issue 8: Blocked Stormwater Drain (2 reports)
    PilotIssueSpec(
        issue_code="ISS-DRAIN-MALLESHWARAM",
        title="Silted Stormwater Drain Causing Waterlogging on 8th Cross",
        category="Drainage Blockage",
        status="OPEN",
        primary_latitude=13.00310,
        primary_longitude=77.57020,
        expected_priority_level="MEDIUM",
        notes="Monsoon runoff backup into adjoining properties.",
    ),
    # Issue 9: Traffic Signal Controller Failure (2 reports)
    PilotIssueSpec(
        issue_code="ISS-SIGNAL-WHITEFIELD",
        title="Stuck Yellow Flashing Traffic Signal at ITPL Main Junction",
        category="Traffic Signal Failure",
        status="OPEN",
        primary_latitude=12.98600,
        primary_longitude=77.73150,
        expected_priority_level="HIGH",
        notes="Intersection traffic jam during morning peak.",
    ),
    # Issue 10: Low-Priority Minor Road Surface Spall (1 report)
    PilotIssueSpec(
        issue_code="ISS-MINOR-POTHOLE-HEBBAL",
        title="Shallow Surface Depression on Low-Speed Residential Cul-de-sac",
        category="Pothole",
        status="OPEN",
        primary_latitude=13.03580,
        primary_longitude=77.59700,
        expected_priority_level="LOW",
        notes="Low-traffic minor defect, lowest priority band.",
    ),
    # Issue 11: Successfully Resolved Municipal Defect (Closed Issue)
    PilotIssueSpec(
        issue_code="ISS-RESOLVED-POTHOLE-CUBBON",
        title="Repaired Bitumen Pothole near Cubbon Park Gate",
        category="Pothole",
        status="RESOLVED",
        primary_latitude=12.97500,
        primary_longitude=77.59100,
        expected_priority_level="LOW",
        notes="Resolution completed and verified by division engineer.",
    ),
    # Issue 12: Formally Closed Defect (Administrative Closure)
    PilotIssueSpec(
        issue_code="ISS-CLOSED-GARBAGE-ULSOOR",
        title="Cleared Garbage Blackspot at Ulsoor Lake Perimeter",
        category="Garbage",
        status="CLOSED",
        primary_latitude=12.98200,
        primary_longitude=77.62000,
        expected_priority_level="LOW",
        notes="Cleaned and barricaded. Closed defect entity.",
    ),
]


# ---------------------------------------------------------------------------
# 2. 40 Synthetic Citizen Reports
# ---------------------------------------------------------------------------

PILOT_REPORTS: list[PilotReportSpec] = [
    # --- Issue 1 Cluster: MG Road School Pothole (8 reports linked) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000001",
        tracking_id="REP-202609-MG001",
        title="Massive dangerous pothole near Bishop Cotton school gate",
        description="Large deep pothole directly outside school gate on MG Road. Several two-wheelers skidded this morning during drop-off.",
        category="Pothole",
        severity="HIGH",
        latitude=12.97160,
        longitude=77.59460,
        address="Near Bishop Cotton School Gate, MG Road, Ward 111",
        citizen_name="Demo Citizen Alpha",
        citizen_phone="+91-9876500001",
        citizen_email="citizen.alpha@example.synthetic",
        citizen_postal_code="560001",
        evidence_urls=["/uploads/pilot_mg_pothole_1.jpg", "/uploads/pilot_mg_pothole_1b.jpg"],
        days_ago=5.0,
        status="PRIORITIZED",
        issue_code="ISS-MG-POTHOLE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000002",
        tracking_id="REP-202609-MG002",
        title="Severe crater in the middle of MG Road road lane",
        description="Dangerous crater causing severe bumper-to-bumper traffic near the school cross. Needs quick asphalt patch work.",
        category="Pothole",
        severity="HIGH",
        latitude=12.97168,
        longitude=77.59466,
        address="Opposite Bishop Cotton School, MG Road, Ward 111",
        citizen_name="Demo Citizen Beta",
        citizen_phone="+91-9876500002",
        citizen_email="citizen.beta@example.synthetic",
        citizen_postal_code="560001",
        evidence_urls=["/uploads/pilot_mg_pothole_2.jpg"],
        days_ago=4.5,
        status="PRIORITIZED",
        issue_code="ISS-MG-POTHOLE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000003",
        tracking_id="REP-202609-MG003",
        title="Deep road hole causing car rim damage",
        description="Broken road surface right near school entrance. Very dangerous after sunset when lighting is dim.",
        category="Pothole",
        severity="MEDIUM",
        latitude=12.97155,
        longitude=77.59458,
        address="MG Road near School Junction, Ward 111",
        citizen_name="Demo Citizen Gamma",
        citizen_phone="+91-9876500003",
        citizen_email="citizen.gamma@example.synthetic",
        citizen_postal_code="560001",
        evidence_urls=["/uploads/pilot_mg_pothole_3.jpg"],
        days_ago=4.0,
        status="PRIORITIZED",
        issue_code="ISS-MG-POTHOLE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000004",
        tracking_id="REP-202609-MG004",
        title="Huge pothole on arterial road lane",
        description="Water accumulated in large pothole in front of school gate. Water hides the true depth.",
        category="Pothole",
        severity="HIGH",
        latitude=12.97162,
        longitude=77.59464,
        address="MG Road Arterial Lane, Ward 111",
        citizen_name="Demo Citizen Delta",
        citizen_phone="+91-9876500004",
        citizen_email="citizen.delta@example.synthetic",
        citizen_postal_code="560001",
        evidence_urls=["/uploads/pilot_mg_pothole_4.jpg"],
        days_ago=3.0,
        status="PRIORITIZED",
        issue_code="ISS-MG-POTHOLE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000005",
        tracking_id="REP-202609-MG005",
        title="School children crossing hazard due to pothole",
        description="Autos swerving into opposite lane to avoid deep pothole on MG Road school stretch.",
        category="Pothole",
        severity="HIGH",
        latitude=12.97158,
        longitude=77.59462,
        address="Bishop Cotton School Perimeter, MG Road",
        citizen_name="Demo Citizen Epsilon",
        citizen_phone="+91-9876500005",
        citizen_email="citizen.epsilon@example.synthetic",
        citizen_postal_code="560001",
        evidence_urls=[],  # No evidence image
        days_ago=2.0,
        status="PRIORITIZED",
        issue_code="ISS-MG-POTHOLE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000006",
        tracking_id="REP-202609-MG006",
        title="Pavement road fracture next to school entrance",
        description="Deep crater expanding in size after rain. Road asphalt crumbling.",
        category="Pothole",
        severity="MEDIUM",
        latitude=12.97164,
        longitude=77.59455,
        address="MG Road School crosswalk, Ward 111",
        citizen_name="Demo Citizen Zeta",
        citizen_phone="+91-9876500006",
        citizen_email="citizen.zeta@example.synthetic",
        citizen_postal_code="560001",
        evidence_urls=["/uploads/pilot_mg_pothole_6.jpg"],
        days_ago=1.5,
        status="PRIORITIZED",
        issue_code="ISS-MG-POTHOLE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000007",
        tracking_id="REP-202609-MG007",
        title="Bad pothole causing heavy congestion",
        description="Vehicles crawling at 5kmph to navigate past deep hole on MG Road.",
        category="Pothole",
        severity="MEDIUM",
        latitude=12.97161,
        longitude=77.59467,
        address="MG Road Westbound Carriage, Ward 111",
        citizen_name="Demo Citizen Eta",
        citizen_phone="+91-9876500007",
        citizen_email="citizen.eta@example.synthetic",
        citizen_postal_code="560001",
        evidence_urls=["/uploads/pilot_mg_pothole_7.jpg"],
        days_ago=1.0,
        status="PRIORITIZED",
        issue_code="ISS-MG-POTHOLE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000008",
        tracking_id="REP-202609-MG008",
        title="Multiple tire punctures from sharp asphalt edge",
        description="Deep crater with sharp gravel edge near school gate on MG road.",
        category="Pothole",
        severity="HIGH",
        latitude=12.97159,
        longitude=77.59461,
        address="MG Road near School Entry, Ward 111",
        citizen_name="Demo Citizen Theta",
        citizen_phone="+91-9876500008",
        citizen_email="citizen.theta@example.synthetic",
        citizen_postal_code="560001",
        evidence_urls=["/uploads/pilot_mg_pothole_8.jpg"],
        days_ago=0.2,
        status="PRIORITIZED",
        issue_code="ISS-MG-POTHOLE",
    ),

    # --- Candidate 1: Pending Match on MG Road Pothole (Vague complaint within 10m) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000009",
        tracking_id="REP-202609-CAND01",
        title="Dangerous road damage near school",
        description="Very dangerous road condition here right in front of the school. Needs inspection.",
        category="Pothole",
        severity="MEDIUM",
        latitude=12.97165,
        longitude=77.59465,
        address="MG Road School crosswalk, Ward 111",
        citizen_name="Demo Citizen Iota",
        citizen_phone="+91-9876500009",
        citizen_email="citizen.iota@example.synthetic",
        citizen_postal_code="560001",
        evidence_urls=["/uploads/pilot_vague_mg_1.jpg"],
        days_ago=0.3,
        status="VERIFICATION_REQUIRED",
        issue_code=None,  # Unlinked, pending candidate review
    ),

    # --- Issue 2: Severe Single Emergency Defect (Open Manhole) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000010",
        tracking_id="REP-202609-MANHOLE01",
        title="Open manhole chamber completely missing iron cover",
        description="Severe emergency: deep drainage manhole uncovered on busy pedestrian walkway on Residency Road. Immediate fall hazard!",
        category="Open Manhole",
        severity="CRITICAL",
        latitude=12.97250,
        longitude=77.60100,
        address="Near Metro Station Pillar 124, Residency Road",
        citizen_name="Demo Citizen Kappa",
        citizen_phone="+91-9876500010",
        citizen_email="citizen.kappa@example.synthetic",
        citizen_postal_code="560025",
        evidence_urls=["/uploads/pilot_open_manhole_1.jpg", "/uploads/pilot_open_manhole_1b.jpg"],
        days_ago=0.1,
        status="PRIORITIZED",
        issue_code="ISS-OPEN-MANHOLE-RESIDENCY",
    ),

    # --- Candidate 2: Pending Duplicate Candidate for Open Manhole ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000011",
        tracking_id="REP-202609-CAND02",
        title="Drain cover broken and pit exposed",
        description="Exposed deep pit on pavement near metro pillar on Residency road. Someone placed a tree branch inside to warn walkers.",
        category="Open Manhole",
        severity="HIGH",
        latitude=12.97255,
        longitude=77.60105,
        address="Residency Road Metro Pillar 125, Ward 112",
        citizen_name="Demo Citizen Lambda",
        citizen_phone="+91-9876500011",
        citizen_email="citizen.lambda@example.synthetic",
        citizen_postal_code="560025",
        evidence_urls=["/uploads/pilot_open_manhole_branch.jpg"],
        days_ago=0.05,
        status="VERIFICATION_REQUIRED",
        issue_code=None,  # Unlinked, pending candidate review
    ),

    # --- Issue 3: City Market Garbage Dumping (5 reports linked) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000012",
        tracking_id="REP-202609-GARB01",
        title="Large pile of decomposing organic garbage at market gate",
        description="Huge pile of rotten vegetable and plastic waste dumped near entry gate 2 of City Market. Foul stench and stray animals.",
        category="Garbage",
        severity="HIGH",
        latitude=12.96020,
        longitude=77.57440,
        address="City Market Gate 2, KR Market, Ward 139",
        citizen_name="Demo Citizen Mu",
        citizen_phone="+91-9876500012",
        citizen_email="citizen.mu@example.synthetic",
        citizen_postal_code="560002",
        evidence_urls=["/uploads/pilot_garbage_market_1.jpg"],
        days_ago=6.0,
        status="PRIORITIZED",
        issue_code="ISS-MARKET-GARBAGE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000013",
        tracking_id="REP-202609-GARB02",
        title="Uncleared market trash blocking pedestrian path",
        description="Garbage dump overflowing onto main walkway. Not cleared for four days.",
        category="Garbage",
        severity="MEDIUM",
        latitude=12.96028,
        longitude=77.57445,
        address="Opposite Wholesale Flower Stalls, City Market",
        citizen_name="Demo Citizen Nu",
        citizen_phone="+91-9876500013",
        citizen_email="citizen.nu@example.synthetic",
        citizen_postal_code="560002",
        evidence_urls=["/uploads/pilot_garbage_market_2.jpg"],
        days_ago=5.0,
        status="PRIORITIZED",
        issue_code="ISS-MARKET-GARBAGE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000014",
        tracking_id="REP-202609-GARB03",
        title="Severe rotten garbage dump attracting cows and dogs",
        description="Decomposing wet waste pile at market entrance causing health hazard.",
        category="Garbage",
        severity="HIGH",
        latitude=12.96015,
        longitude=77.57438,
        address="Market Entry Gate 2 Approach, KR Market",
        citizen_name="Demo Citizen Xi",
        citizen_phone="+91-9876500014",
        citizen_email="citizen.xi@example.synthetic",
        citizen_postal_code="560002",
        evidence_urls=["/uploads/pilot_garbage_market_3.jpg"],
        days_ago=3.5,
        status="PRIORITIZED",
        issue_code="ISS-MARKET-GARBAGE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000015",
        tracking_id="REP-202609-GARB04",
        title="Commercial packaging waste dumped on road",
        description="Cardboard boxes and plastic packing waste piled up next to rotten vegetables.",
        category="Garbage",
        severity="MEDIUM",
        latitude=12.96022,
        longitude=77.57442,
        address="KR Market Bus Stand Perimeter",
        citizen_name="Demo Citizen Omicron",
        citizen_phone="+91-9876500015",
        citizen_email="citizen.omicron@example.synthetic",
        citizen_postal_code="560002",
        evidence_urls=["/uploads/pilot_garbage_market_4.jpg"],
        days_ago=2.0,
        status="PRIORITIZED",
        issue_code="ISS-MARKET-GARBAGE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000016",
        tracking_id="REP-202609-GARB05",
        title="Trash mound expanding onto active lane",
        description="Huge garbage heap now spilling onto road carriageway, blocking delivery trucks.",
        category="Garbage",
        severity="HIGH",
        latitude=12.96018,
        longitude=77.57441,
        address="City Market Gate 2, KR Market",
        citizen_name="Demo Citizen Pi",
        citizen_phone="+91-9876500016",
        citizen_email="citizen.pi@example.synthetic",
        citizen_postal_code="560002",
        evidence_urls=[],  # No evidence
        days_ago=0.8,
        status="PRIORITIZED",
        issue_code="ISS-MARKET-GARBAGE",
    ),

    # --- Candidate 3: Pending Duplicate Candidate for Garbage Dumping ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000017",
        tracking_id="REP-202609-CAND03",
        title="Foul smelling refuse near vegetable market",
        description="Bad odor from huge pile of rotting trash near the main vegetable loading bay at KR market.",
        category="Garbage",
        severity="MEDIUM",
        latitude=12.96026,
        longitude=77.57448,
        address="Vegetable Loading Bay, City Market",
        citizen_name="Demo Citizen Rho",
        citizen_phone="+91-9876500017",
        citizen_email="citizen.rho@example.synthetic",
        citizen_postal_code="560002",
        evidence_urls=["/uploads/pilot_garbage_cand_3.jpg"],
        days_ago=0.4,
        status="VERIFICATION_REQUIRED",
        issue_code=None,  # Pending candidate
    ),

    # --- Issue 4: Jayanagar Water Pipe Rupture (4 reports linked) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000018",
        tracking_id="REP-202609-WATER01",
        title="Clean drinking water pipe burst flooding road",
        description="Potable water pipe fractured underground on 4th Main Jayanagar. Water gushing out like fountain across street.",
        category="Water Leakage",
        severity="HIGH",
        latitude=12.92980,
        longitude=77.58320,
        address="Opposite Post Office, 4th Main Road, Jayanagar 4th Block",
        citizen_name="Demo Citizen Sigma",
        citizen_phone="+91-9876500018",
        citizen_email="citizen.sigma@example.synthetic",
        citizen_postal_code="560011",
        evidence_urls=["/uploads/pilot_water_burst_1.jpg"],
        days_ago=2.5,
        status="PRIORITIZED",
        issue_code="ISS-WATER-BURST-JAYANAGAR",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000019",
        tracking_id="REP-202609-WATER02",
        title="Heavy water leakage eroding road foundation",
        description="Massive stream of fresh water flowing continuously down 4th Main slope. Thousands of liters wasted.",
        category="Water Leakage",
        severity="HIGH",
        latitude=12.92985,
        longitude=77.58325,
        address="4th Main Road near Post Office, Jayanagar 4th Block",
        citizen_name="Demo Citizen Tau",
        citizen_phone="+91-9876500019",
        citizen_email="citizen.tau@example.synthetic",
        citizen_postal_code="560011",
        evidence_urls=["/uploads/pilot_water_burst_2.jpg"],
        days_ago=2.0,
        status="PRIORITIZED",
        issue_code="ISS-WATER-BURST-JAYANAGAR",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000020",
        tracking_id="REP-202609-WATER03",
        title="Underground pipeline leak submerging sidewalk",
        description="Water main broken, flooding pavement and entering basement car park of commercial building.",
        category="Water Leakage",
        severity="HIGH",
        latitude=12.92978,
        longitude=77.58318,
        address="Commercial Complex, 4th Main, Jayanagar",
        citizen_name="Demo Citizen Upsilon",
        citizen_phone="+91-9876500020",
        citizen_email="citizen.upsilon@example.synthetic",
        citizen_postal_code="560011",
        evidence_urls=["/uploads/pilot_water_burst_3.jpg"],
        days_ago=1.2,
        status="PRIORITIZED",
        issue_code="ISS-WATER-BURST-JAYANAGAR",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000021",
        tracking_id="REP-202609-WATER04",
        title="Municipal water gushing continuously onto road",
        description="High volume water pipeline rupture. Pressure dropping in neighborhood taps.",
        category="Water Leakage",
        severity="MEDIUM",
        latitude=12.92982,
        longitude=77.58322,
        address="4th Main, Jayanagar Ward 153",
        citizen_name="Demo Citizen Phi",
        citizen_phone="+91-9876500021",
        citizen_email="citizen.phi@example.synthetic",
        citizen_postal_code="560011",
        evidence_urls=["/uploads/pilot_water_burst_4.jpg"],
        days_ago=0.5,
        status="PRIORITIZED",
        issue_code="ISS-WATER-BURST-JAYANAGAR",
    ),

    # --- Candidate 4: Pending Duplicate Candidate for Water Leak ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000022",
        tracking_id="REP-202609-CAND04",
        title="Street flooded with clean tap water",
        description="Fresh water stream rushing across Jayanagar 4th main road near post office junction. Pipe broken.",
        category="Water Leakage",
        severity="MEDIUM",
        latitude=12.92987,
        longitude=77.58330,
        address="4th Main Junction, Jayanagar",
        citizen_name="Demo Citizen Chi",
        citizen_phone="+91-9876500022",
        citizen_email="citizen.chi@example.synthetic",
        citizen_postal_code="560011",
        evidence_urls=["/uploads/pilot_water_cand_4.jpg"],
        days_ago=0.2,
        status="VERIFICATION_REQUIRED",
        issue_code=None,  # Pending candidate
    ),

    # --- Issue 5: Indiranagar Streetlight Corridor (3 reports linked) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000023",
        tracking_id="REP-202609-LIGHT01",
        title="Dark streetlights along 100ft road Indiranagar",
        description="Multiple consecutive streetlight poles completely unlit on 100ft road between 12th Main and 14th Main.",
        category="Broken Streetlight",
        severity="MEDIUM",
        latitude=12.97840,
        longitude=77.64080,
        address="100ft Road between 12th & 14th Main, Indiranagar",
        citizen_name="Demo Citizen Psi",
        citizen_phone="+91-9876500023",
        citizen_email="citizen.psi@example.synthetic",
        citizen_postal_code="560038",
        evidence_urls=["/uploads/pilot_dark_street_1.jpg"],
        days_ago=7.0,
        status="PRIORITIZED",
        issue_code="ISS-STREETLIGHT-INDIRANAGAR",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000024",
        tracking_id="REP-202609-LIGHT02",
        title="Entire stretch of streetlights dark at night",
        description="Street lights not turning on after dusk on 100ft road corridor. Pitch black pedestrian crossings.",
        category="Broken Streetlight",
        severity="MEDIUM",
        latitude=12.97848,
        longitude=77.64088,
        address="100ft Road 13th Main Cross, Indiranagar",
        citizen_name="Demo Citizen Omega",
        citizen_phone="+91-9876500024",
        citizen_email="citizen.omega@example.synthetic",
        citizen_postal_code="560038",
        evidence_urls=["/uploads/pilot_dark_street_2.jpg"],
        days_ago=5.5,
        status="PRIORITIZED",
        issue_code="ISS-STREETLIGHT-INDIRANAGAR",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000025",
        tracking_id="REP-202609-LIGHT03",
        title="Lamp post timer failed, lights off all night",
        description="Streetlights along 100 feet road remain completely dark throughout the night.",
        category="Broken Streetlight",
        severity="LOW",
        latitude=12.97835,
        longitude=77.64075,
        address="100ft Road Corridor, Indiranagar",
        citizen_name="Demo Citizen A1",
        citizen_phone="+91-9876500025",
        citizen_email="citizen.a1@example.synthetic",
        citizen_postal_code="560038",
        evidence_urls=[],  # No image
        days_ago=4.0,
        status="PRIORITIZED",
        issue_code="ISS-STREETLIGHT-INDIRANAGAR",
    ),

    # --- Candidate 5: Pending Duplicate Candidate for Streetlight ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000026",
        tracking_id="REP-202609-CAND05",
        title="No lighting on 100 ft road stretch",
        description="Lights are switched off on 100 ft road Indiranagar. Very unsafe for women walking home from metro station.",
        category="Broken Streetlight",
        severity="MEDIUM",
        latitude=12.97842,
        longitude=77.64082,
        address="Near 100ft Road Metro Exit, Indiranagar",
        citizen_name="Demo Citizen A2",
        citizen_phone="+91-9876500026",
        citizen_email="citizen.a2@example.synthetic",
        citizen_postal_code="560038",
        evidence_urls=["/uploads/pilot_streetlight_cand_5.jpg"],
        days_ago=0.15,
        status="VERIFICATION_REQUIRED",
        issue_code=None,  # Pending candidate
    ),

    # --- Issue 6: Brigade Road Damaged Footpath (2 reports linked) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000027",
        tracking_id="REP-202609-FOOT01",
        title="Loose broken concrete paver slabs on Brigade Road",
        description="Slabs on pedestrian walkway loose, displaced, and rocking. Elderly person tripped and fell yesterday.",
        category="Damaged Footpath",
        severity="MEDIUM",
        latitude=12.97390,
        longitude=77.60750,
        address="Brigade Road Pedestrian Walkway, Ward 111",
        citizen_name="Demo Citizen A3",
        citizen_phone="+91-9876500027",
        citizen_email="citizen.a3@example.synthetic",
        citizen_postal_code="560025",
        evidence_urls=["/uploads/pilot_footpath_1.jpg"],
        days_ago=8.0,
        status="PRIORITIZED",
        issue_code="ISS-FOOTPATH-BRIGADE",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000028",
        tracking_id="REP-202609-FOOT02",
        title="Cracked pavement tiles trip hazard on shopping street",
        description="Broken paving blocks with deep gaps in sidewalk near Rex theater junction.",
        category="Damaged Footpath",
        severity="MEDIUM",
        latitude=12.97395,
        longitude=77.60755,
        address="Brigade Road near Rex Junction, Ward 111",
        citizen_name="Demo Citizen A4",
        citizen_phone="+91-9876500028",
        citizen_email="citizen.a4@example.synthetic",
        citizen_postal_code="560025",
        evidence_urls=["/uploads/pilot_footpath_2.jpg"],
        days_ago=6.5,
        status="PRIORITIZED",
        issue_code="ISS-FOOTPATH-BRIGADE",
    ),

    # --- Issue 7: Fallen Tree in Koramangala (2 reports linked) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000029",
        tracking_id="REP-202609-TREE01",
        title="Large uprooted tree branch blocking residential street",
        description="Heavy tree branch fell across 1st Cross road in Koramangala 5th block. Cars cannot pass through.",
        category="Fallen Tree",
        severity="HIGH",
        latitude=12.93520,
        longitude=77.62450,
        address="1st Cross, 5th Block Koramangala",
        citizen_name="Demo Citizen A5",
        citizen_phone="+91-9876500029",
        citizen_email="citizen.a5@example.synthetic",
        citizen_postal_code="560095",
        evidence_urls=["/uploads/pilot_tree_1.jpg", "/uploads/pilot_tree_1b.jpg"],
        days_ago=1.8,
        status="PRIORITIZED",
        issue_code="ISS-TREE-KORAMANGALA",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000030",
        tracking_id="REP-202609-TREE02",
        title="Fallen branches tangled with low-hanging overhead cables",
        description="Tree limbs broke during squall, resting on electric and internet wires across the lane.",
        category="Fallen Tree",
        severity="HIGH",
        latitude=12.93526,
        longitude=77.62454,
        address="Koramangala 5th Block, near Park Gate",
        citizen_name="Demo Citizen A6",
        citizen_phone="+91-9876500030",
        citizen_email="citizen.a6@example.synthetic",
        citizen_postal_code="560095",
        evidence_urls=["/uploads/pilot_tree_2.jpg"],
        days_ago=1.0,
        status="PRIORITIZED",
        issue_code="ISS-TREE-KORAMANGALA",
    ),

    # --- Issue 8: Malleshwaram Blocked Stormwater Drain (2 reports linked) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000031",
        tracking_id="REP-202609-DRAIN01",
        title="Stormwater roadside gutter blocked solid with silt and debris",
        description="Rainwater gutter on 8th Cross choked with construction debris and fallen leaves. Water stagnating.",
        category="Drainage Blockage",
        severity="MEDIUM",
        latitude=13.00310,
        longitude=77.57020,
        address="8th Cross, Margosa Road, Malleshwaram",
        citizen_name="Demo Citizen A7",
        citizen_phone="+91-9876500031",
        citizen_email="citizen.a7@example.synthetic",
        citizen_postal_code="560003",
        evidence_urls=["/uploads/pilot_drain_1.jpg"],
        days_ago=4.2,
        status="PRIORITIZED",
        issue_code="ISS-DRAIN-MALLESHWARAM",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000032",
        tracking_id="REP-202609-DRAIN02",
        title="Stagnant black drain water overflowing onto road",
        description="Clogged storm drain backing up during rain showers. Mosquito breeding in stagnant water.",
        category="Drainage Blockage",
        severity="MEDIUM",
        latitude=13.00316,
        longitude=77.57025,
        address="Margosa Road 8th Cross Junction, Malleshwaram",
        citizen_name="Demo Citizen A8",
        citizen_phone="+91-9876500032",
        citizen_email="citizen.a8@example.synthetic",
        citizen_postal_code="560003",
        evidence_urls=["/uploads/pilot_drain_2.jpg"],
        days_ago=3.0,
        status="PRIORITIZED",
        issue_code="ISS-DRAIN-MALLESHWARAM",
    ),

    # --- Issue 9: Whitefield Traffic Signal Failure (2 reports linked) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000033",
        tracking_id="REP-202609-SIG01",
        title="Traffic signal cycling stuck on amber light",
        description="Traffic light malfunction at ITPL main junction. All 4 sides flashing yellow, complete gridlock.",
        category="Traffic Signal Failure",
        severity="HIGH",
        latitude=12.98600,
        longitude=77.73150,
        address="ITPL Main Road Junction, Whitefield",
        citizen_name="Demo Citizen A9",
        citizen_phone="+91-9876500033",
        citizen_email="citizen.a9@example.synthetic",
        citizen_postal_code="560066",
        evidence_urls=["/uploads/pilot_signal_1.jpg"],
        days_ago=0.6,
        status="PRIORITIZED",
        issue_code="ISS-SIGNAL-WHITEFIELD",
    ),
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000034",
        tracking_id="REP-202609-SIG02",
        title="Signal controller dead at major tech park junction",
        description="No traffic lights working at ITPL junction. Vehicles crossing blindly, dangerous near-misses.",
        category="Traffic Signal Failure",
        severity="HIGH",
        latitude=12.98608,
        longitude=77.73155,
        address="ITPL Main Gate Signal, Whitefield",
        citizen_name="Demo Citizen B1",
        citizen_phone="+91-9876500034",
        citizen_email="citizen.b1@example.synthetic",
        citizen_postal_code="560066",
        evidence_urls=["/uploads/pilot_signal_2.jpg"],
        days_ago=0.3,
        status="PRIORITIZED",
        issue_code="ISS-SIGNAL-WHITEFIELD",
    ),

    # --- Candidate 6: Pending Duplicate Candidate for Traffic Signal ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000035",
        tracking_id="REP-202609-CAND06",
        title="Lights not functioning at ITPL road junction",
        description="Traffic light signal is out at ITPL road intersection. Major traffic jam backing up to Hope Farm.",
        category="Traffic Signal Failure",
        severity="HIGH",
        latitude=12.98604,
        longitude=77.73152,
        address="ITPL Intersection, Whitefield",
        citizen_name="Demo Citizen B2",
        citizen_phone="+91-9876500035",
        citizen_email="citizen.b2@example.synthetic",
        citizen_postal_code="560066",
        evidence_urls=["/uploads/pilot_signal_cand_6.jpg"],
        days_ago=0.1,
        status="VERIFICATION_REQUIRED",
        issue_code=None,  # Pending candidate
    ),

    # --- Issue 10: Low Priority Minor Pothole (1 report linked) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000036",
        tracking_id="REP-202609-MINOR01",
        title="Shallow small road depression on quiet lane",
        description="Minor shallow dip in asphalt on dead-end residential street in Hebbal. Minor vehicle inconvenience.",
        category="Pothole",
        severity="LOW",
        latitude=13.03580,
        longitude=77.59700,
        address="1st Main, Kempapura Residential Layout, Hebbal",
        citizen_name="Demo Citizen B3",
        citizen_phone="+91-9876500036",
        citizen_email="citizen.b3@example.synthetic",
        citizen_postal_code="560024",
        evidence_urls=["/uploads/pilot_minor_pothole.jpg"],
        days_ago=12.0,
        status="PRIORITIZED",
        issue_code="ISS-MINOR-POTHOLE-HEBBAL",
    ),

    # --- Issue 11: Resolved Defect Report (Linked to RESOLVED issue) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000037",
        tracking_id="REP-202609-RESOLV01",
        title="Pothole near Cubbon Park gate (repaired)",
        description="Road surface was damaged outside Cubbon park gate, road crew completed bitumen patch.",
        category="Pothole",
        severity="LOW",
        latitude=12.97500,
        longitude=77.59100,
        address="Cubbon Park Gate 3, Kasturba Road",
        citizen_name="Demo Citizen B4",
        citizen_phone="+91-9876500037",
        citizen_email="citizen.b4@example.synthetic",
        citizen_postal_code="560001",
        evidence_urls=["/uploads/pilot_resolved_pothole.jpg"],
        days_ago=14.0,
        status="RESOLVED",
        issue_code="ISS-RESOLVED-POTHOLE-CUBBON",
    ),

    # --- Issue 12: Closed Defect Report (Linked to CLOSED issue) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000038",
        tracking_id="REP-202609-CLOSE01",
        title="Garbage blackspot near Ulsoor lake",
        description="Litter and plastic containers along lakeside pathway. Area was cleared and dustbins installed.",
        category="Garbage",
        severity="LOW",
        latitude=12.98200,
        longitude=77.62000,
        address="Ulsoor Lake Promenade North Gate",
        citizen_name="Demo Citizen B5",
        citizen_phone="+91-9876500038",
        citizen_email="citizen.b5@example.synthetic",
        citizen_postal_code="560042",
        evidence_urls=["/uploads/pilot_closed_garbage.jpg"],
        days_ago=15.0,
        status="CLOSED",
        issue_code="ISS-CLOSED-GARBAGE-ULSOOR",
    ),

    # --- Report 39: Null Island GPS Coordinate Failure (0.0, 0.0) ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000039",
        tracking_id="REP-202609-NULLGPS01",
        title="Damaged road pavement with unacquired GPS coordinates",
        description="Citizen submitted report while phone was in airplane mode or GPS hardware timed out. Coords are 0.0, 0.0.",
        category="Pothole",
        severity="LOW",
        latitude=0.0,
        longitude=0.0,
        address="Location Unavailable (GPS Acquisition Failed)",
        citizen_name="Demo Citizen B6",
        citizen_phone="+91-9876500039",
        citizen_email="citizen.b6@example.synthetic",
        citizen_postal_code="560000",
        evidence_urls=["/uploads/pilot_null_island.jpg"],
        days_ago=0.5,
        status="SUBMITTED",
        issue_code=None,  # Standalone
    ),

    # --- Report 40: Standalone Unmatched Independent Defect ---
    PilotReportSpec(
        report_id="11111111-0001-0000-0000-000000000040",
        tracking_id="REP-202609-STANDALONE01",
        title="Exposed electrical wiring on utility transformer pole",
        description="Live copper cables dangling exposed from BESCOM utility pole on 11th Main Malleshwaram. Dangerous electrical hazard.",
        category="Other",
        severity="HIGH",
        latitude=13.00750,
        longitude=77.56820,
        address="11th Main Road near Post Office, Malleshwaram",
        citizen_name="Demo Citizen B7",
        citizen_phone="+91-9876500040",
        citizen_email="citizen.b7@example.synthetic",
        citizen_postal_code="560003",
        evidence_urls=["/uploads/pilot_exposed_wiring.jpg"],
        days_ago=0.1,
        status="SUBMITTED",
        issue_code=None,  # Independent new issue
    ),
]


# ---------------------------------------------------------------------------
# 3. Match Records (Pending candidates, approved links, rejected candidates)
# ---------------------------------------------------------------------------

PILOT_MATCHES: list[PilotMatchSpec] = [
    # 6 PENDING Candidate Matches for Live Officer Review
    PilotMatchSpec(
        match_code="MATCH-CAND-01",
        report_tracking_id="REP-202609-CAND01",
        candidate_issue_code="ISS-MG-POTHOLE",
        action="CANDIDATE",
        status="PENDING",
        combined_score=0.64,
        text_similarity=0.48,
        distance_meters=7.5,
        category_match=1.0,
        reasoning=[
            "TEXT_SIMILARITY=0.4800 (weight=0.40)",
            "DISTANCE=7.5m -> score=0.8500 (weight=0.35)",
            "CATEGORY=Exact match (weight=0.25)",
            "ACTION=CANDIDATE(threshold=0.45)",
        ],
        reviewer_id=None,
        review_notes=None,
    ),
    PilotMatchSpec(
        match_code="MATCH-CAND-02",
        report_tracking_id="REP-202609-CAND02",
        candidate_issue_code="ISS-OPEN-MANHOLE-RESIDENCY",
        action="CANDIDATE",
        status="PENDING",
        combined_score=0.67,
        text_similarity=0.55,
        distance_meters=6.2,
        category_match=1.0,
        reasoning=[
            "TEXT_SIMILARITY=0.5500 (weight=0.40)",
            "DISTANCE=6.2m -> score=0.8760 (weight=0.35)",
            "CATEGORY=Exact match (weight=0.25)",
            "ACTION=CANDIDATE(threshold=0.45)",
        ],
        reviewer_id=None,
        review_notes=None,
    ),
    PilotMatchSpec(
        match_code="MATCH-CAND-03",
        report_tracking_id="REP-202609-CAND03",
        candidate_issue_code="ISS-MARKET-GARBAGE",
        action="CANDIDATE",
        status="PENDING",
        combined_score=0.58,
        text_similarity=0.42,
        distance_meters=12.0,
        category_match=1.0,
        reasoning=[
            "TEXT_SIMILARITY=0.4200 (weight=0.40)",
            "DISTANCE=12.0m -> score=0.7600 (weight=0.35)",
            "CATEGORY=Exact match (weight=0.25)",
            "ACTION=CANDIDATE(threshold=0.45)",
        ],
        reviewer_id=None,
        review_notes=None,
    ),
    PilotMatchSpec(
        match_code="MATCH-CAND-04",
        report_tracking_id="REP-202609-CAND04",
        candidate_issue_code="ISS-WATER-BURST-JAYANAGAR",
        action="CANDIDATE",
        status="PENDING",
        combined_score=0.62,
        text_similarity=0.50,
        distance_meters=11.2,
        category_match=1.0,
        reasoning=[
            "TEXT_SIMILARITY=0.5000 (weight=0.40)",
            "DISTANCE=11.2m -> score=0.7760 (weight=0.35)",
            "CATEGORY=Exact match (weight=0.25)",
            "ACTION=CANDIDATE(threshold=0.45)",
        ],
        reviewer_id=None,
        review_notes=None,
    ),
    PilotMatchSpec(
        match_code="MATCH-CAND-05",
        report_tracking_id="REP-202609-CAND05",
        candidate_issue_code="ISS-STREETLIGHT-INDIRANAGAR",
        action="CANDIDATE",
        status="PENDING",
        combined_score=0.66,
        text_similarity=0.58,
        distance_meters=3.5,
        category_match=1.0,
        reasoning=[
            "TEXT_SIMILARITY=0.5800 (weight=0.40)",
            "DISTANCE=3.5m -> score=0.9300 (weight=0.35)",
            "CATEGORY=Exact match (weight=0.25)",
            "ACTION=CANDIDATE(threshold=0.45)",
        ],
        reviewer_id=None,
        review_notes=None,
    ),
    PilotMatchSpec(
        match_code="MATCH-CAND-06",
        report_tracking_id="REP-202609-CAND06",
        candidate_issue_code="ISS-SIGNAL-WHITEFIELD",
        action="CANDIDATE",
        status="PENDING",
        combined_score=0.68,
        text_similarity=0.62,
        distance_meters=4.8,
        category_match=1.0,
        reasoning=[
            "TEXT_SIMILARITY=0.6200 (weight=0.40)",
            "DISTANCE=4.8m -> score=0.9040 (weight=0.35)",
            "CATEGORY=Exact match (weight=0.25)",
            "ACTION=CANDIDATE(threshold=0.45)",
        ],
        reviewer_id=None,
        review_notes=None,
    ),

    # 4 REJECTED Matches (Historical Audit Demonstrations)
    PilotMatchSpec(
        match_code="MATCH-REJ-01",
        report_tracking_id="REP-202609-MG003",
        candidate_issue_code="ISS-OPEN-MANHOLE-RESIDENCY",
        action="CANDIDATE",
        status="REJECTED",
        combined_score=0.46,
        text_similarity=0.35,
        distance_meters=45.0,
        category_match=0.0,
        reasoning=[
            "TEXT_SIMILARITY=0.3500 (weight=0.40)",
            "DISTANCE=45.0m -> score=0.1000 (weight=0.35)",
            "CATEGORY=Mismatch (weight=0.25)",
            "ACTION=REJECTED(manual_officer_override)",
        ],
        reviewer_id="officer-triage-42",
        review_notes="Rejected: distinct issue type (pothole vs manhole) and distant.",
    ),
    PilotMatchSpec(
        match_code="MATCH-REJ-02",
        report_tracking_id="REP-202609-GARB02",
        candidate_issue_code="ISS-MG-POTHOLE",
        action="CANDIDATE",
        status="REJECTED",
        combined_score=0.48,
        text_similarity=0.40,
        distance_meters=40.0,
        category_match=0.0,
        reasoning=[
            "TEXT_SIMILARITY=0.4000 (weight=0.40)",
            "DISTANCE=40.0m -> score=0.2000 (weight=0.35)",
            "CATEGORY=Mismatch (weight=0.25)",
            "ACTION=REJECTED(manual_officer_override)",
        ],
        reviewer_id="officer-triage-42",
        review_notes="Rejected: unrelated defect classes.",
    ),
    PilotMatchSpec(
        match_code="MATCH-REJ-03",
        report_tracking_id="REP-202609-STANDALONE01",
        candidate_issue_code="ISS-DRAIN-MALLESHWARAM",
        action="CANDIDATE",
        status="REJECTED",
        combined_score=0.47,
        text_similarity=0.38,
        distance_meters=48.0,
        category_match=0.5,
        reasoning=[
            "TEXT_SIMILARITY=0.3800 (weight=0.40)",
            "DISTANCE=48.0m -> score=0.0400 (weight=0.35)",
            "CATEGORY=Bridge (weight=0.25)",
            "ACTION=REJECTED(manual_officer_override)",
        ],
        reviewer_id="officer-triage-18",
        review_notes="Rejected: exposed wiring is BESCOM jurisdiction, not drain issue.",
    ),
    PilotMatchSpec(
        match_code="MATCH-REJ-04",
        report_tracking_id="REP-202609-NULLGPS01",
        candidate_issue_code="ISS-MINOR-POTHOLE-HEBBAL",
        action="CANDIDATE",
        status="REJECTED",
        combined_score=0.49,
        text_similarity=0.45,
        distance_meters=50.0,
        category_match=1.0,
        reasoning=[
            "TEXT_SIMILARITY=0.4500 (weight=0.40)",
            "DISTANCE=Null Island coordinate rejection",
            "ACTION=REJECTED(missing_gps_boundary)",
        ],
        reviewer_id="officer-triage-18",
        review_notes="Rejected: missing GPS cannot be linked to Hebbal.",
    ),
]


# ---------------------------------------------------------------------------
# 4. Exporter and Database Seeder
# ---------------------------------------------------------------------------

def generate_pilot_dataset_dict() -> dict[str, Any]:
    """Return JSON-serializable dictionary representation of the pilot dataset."""
    return {
        "metadata": {
            "title": "CivicSense Controlled Pilot Seed Dataset",
            "version": "1.0.0",
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
            "reports_count": len(PILOT_REPORTS),
            "issues_count": len(PILOT_ISSUES),
            "matches_count": len(PILOT_MATCHES),
            "privacy_statement": (
                "All citizen identities, contact phone numbers, emails, and postal codes "
                "are synthetic demo fixtures. Zero real citizen PII is present."
            ),
        },
        "issues": [asdict(i) for i in PILOT_ISSUES],
        "reports": [asdict(r) for r in PILOT_REPORTS],
        "matches": [asdict(m) for m in PILOT_MATCHES],
    }


def seed_database(db: Session, *, reset: bool = False) -> dict[str, int]:
    """Seed the database with the synthetic pilot dataset.

    Args:
        db: Active SQLAlchemy Session.
        reset: If True, purges existing tables before seeding.

    Returns:
        Summary count dict of created entities.
    """
    from app.models.enums import EvidenceType
    from app.models.evidence import Evidence
    from app.models.issue import Issue
    from app.models.report import Report
    from app.models.report_issue_match import ReportIssueMatch
    from app.services.priority.service import apply_priority_to_issue

    now = datetime.datetime.now(datetime.UTC)

    if reset:
        db.query(ReportIssueMatch).delete()
        db.query(Evidence).delete()
        db.query(Report).delete()
        db.query(Issue).delete()
        db.flush()

    # 1. Create Issues
    issue_map: dict[str, Issue] = {}
    for ispec in PILOT_ISSUES:
        issue = Issue(
            id=uuid.uuid4(),
            title=ispec.title,
            category=ispec.category,
            status=ispec.status,
            primary_latitude=ispec.primary_latitude,
            primary_longitude=ispec.primary_longitude,
            report_count=0,  # will be incremented as reports link
            created_at=now - datetime.timedelta(days=15),
            updated_at=now,
        )
        db.add(issue)
        issue_map[ispec.issue_code] = issue
    db.flush()

    # 2. Create Reports
    report_map: dict[str, Report] = {}
    for rspec in PILOT_REPORTS:
        sub_time = now - datetime.timedelta(days=rspec.days_ago)
        linked_issue = issue_map.get(rspec.issue_code) if rspec.issue_code else None

        report = Report(
            id=uuid.UUID(rspec.report_id),
            tracking_id=rspec.tracking_id,
            description=rspec.description,
            category=rspec.category,
            status=rspec.status,
            latitude=rspec.latitude,
            longitude=rspec.longitude,
            address_hint=rspec.address,
            citizen_name=rspec.citizen_name,
            citizen_phone=rspec.citizen_phone,
            citizen_email=rspec.citizen_email,
            citizen_postal_code=rspec.citizen_postal_code,
            issue_id=linked_issue.id if linked_issue else None,
            created_at=sub_time,
            updated_at=sub_time,
        )
        db.add(report)
        report_map[rspec.tracking_id] = report

        if linked_issue:
            linked_issue.report_count += 1

        # Add mock evidence items
        for ev_url in rspec.evidence_urls:
            ev = Evidence(
                id=uuid.uuid4(),
                report_id=report.id,
                evidence_type=EvidenceType.IMAGE,
                storage_uri=ev_url,
                file_hash=f"sha256_mock_{rspec.tracking_id}",
                file_size_bytes=245_000,
                mime_type="image/jpeg",
                created_at=sub_time,
            )
            db.add(ev)
    db.flush()

    # 3. Create Matches
    for mspec in PILOT_MATCHES:
        rep = report_map.get(mspec.report_tracking_id)
        cand_issue = issue_map.get(mspec.candidate_issue_code)
        if not rep or not cand_issue:
            continue

        match_row = ReportIssueMatch(
            id=uuid.uuid4(),
            report_id=rep.id,
            issue_id=cand_issue.id,
            action=mspec.action,
            status=mspec.status,
            combined_score=mspec.combined_score,
            text_similarity=mspec.text_similarity,
            distance_meters=mspec.distance_meters,
            category_match=mspec.category_match,
            reasoning=mspec.reasoning,
            embedding_model_version="all-MiniLM-L6-v2-v1",
            reviewer_id=mspec.reviewer_id,
            review_notes=mspec.review_notes,
            reviewed_at=(
                now - datetime.timedelta(hours=2)
                if mspec.status in ("APPROVED", "REJECTED")
                else None
            ),
            created_at=rep.created_at,
        )
        db.add(match_row)
    db.flush()

    # 4. Compute and apply priorities across all issues
    for issue in issue_map.values():
        apply_priority_to_issue(db, issue)
    db.flush()
    db.commit()

    return {
        "issues_created": len(issue_map),
        "reports_created": len(report_map),
        "matches_created": len(PILOT_MATCHES),
    }
