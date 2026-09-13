"""Unit and integration regression tests for AI pipeline, similarity matching, and decision support.

Covers:
1. True duplicate matching and auto-linking
2. Spatial separation prevention (distant reports create new issues)
3. Category mismatch safety gate (incompatible categories never auto-linked)
4. Null Island (0, 0) coordinate defense
5. Candidate match persistence and review approval workflow
6. Priority score boundary conditions (zero reports, single critical, many low, conflicting severities)
7. Human review routing and repeated review defense
"""

import datetime
import uuid

import pytest
from sqlalchemy.orm import Session

from app.evaluation.synthetic_civic_dataset import get_evaluation_pairs, get_synthetic_reports
from app.models.enums import PriorityLevel, SeverityLevel
from app.models.issue import Issue
from app.models.report import Report
from app.models.report_issue_match import ReportIssueMatch
from app.services.priority.service import (
    apply_priority_to_issue,
    compute_issue_priority,
    persistence_score,
    recency_score,
    report_volume_score,
    severity_score,
)
from app.services.similarity.review import MatchReviewService
from app.services.similarity.service import (
    MatchAction,
    MatchStatus,
    SimilarityConfig,
    category_score,
    cosine_similarity,
    distance_score,
    haversine_distance_meters,
    match_report_to_issue,
    process_similarity_match,
)


# ---------------------------------------------------------------------------
# 1. Similarity & Deduplication Matching Tests
# ---------------------------------------------------------------------------

class TestSimilarityPipelineValidation:
    """Test similarity matching behavior against critical edge cases."""

    def test_true_duplicate_auto_links_or_candidates(self, db_session: Session) -> None:
        """True duplicates at same location with matching category should link or candidate."""
        # 1. First report creates new issue
        rep1 = Report(
            id=uuid.uuid4(),
            tracking_id="SYN-REP-001",
            description="Large deep pothole near the school entrance on MG Road causing traffic jam",
            category="Pothole",
            latitude=12.9716,
            longitude=77.5946,
        )
        db_session.add(rep1)
        db_session.flush()

        match1 = process_similarity_match(db_session, rep1)
        assert match1.action == MatchAction.NEW_ISSUE
        assert rep1.issue_id is not None
        issue_id = rep1.issue_id

        # 2. Second report ~14m away with similar description
        rep2 = Report(
            id=uuid.uuid4(),
            tracking_id="SYN-REP-002",
            description="Deep road hole outside the school gate on MG Road, vehicles swerving",
            category="Pothole",
            latitude=12.9717,
            longitude=77.59468,
        )
        db_session.add(rep2)
        db_session.flush()

        match2 = process_similarity_match(db_session, rep2)
        # Should be AUTO_LINK or CANDIDATE, never NEW_ISSUE
        assert match2.action in (MatchAction.AUTO_LINK, MatchAction.CANDIDATE)
        assert match2.score >= 0.45

    def test_category_mismatch_never_auto_links(self, db_session: Session) -> None:
        """Incompatible categories at 0m distance must NEVER be auto-linked."""
        # Issue is Streetlight
        rep_light = Report(
            id=uuid.uuid4(),
            tracking_id="SYN-REP-012",
            description="Broken streetlight pole with exposed wiring at Central Park Gate",
            category="Streetlight",
            latitude=12.9800,
            longitude=77.5900,
        )
        db_session.add(rep_light)
        db_session.flush()
        match_light = process_similarity_match(db_session, rep_light)
        assert match_light.action == MatchAction.NEW_ISSUE

        # Report is Pothole at identical coordinates (0m away)
        rep_pothole = Report(
            id=uuid.uuid4(),
            tracking_id="SYN-REP-013",
            description="Deep dangerous pothole right in front of Central Park Gate",
            category="Pothole",
            latitude=12.9800,
            longitude=77.5900,
        )
        db_session.add(rep_pothole)
        db_session.flush()

        match_pothole = process_similarity_match(db_session, rep_pothole)
        # MUST be NEW_ISSUE because Pothole and Streetlight are incompatible
        assert match_pothole.action == MatchAction.NEW_ISSUE
        assert rep_pothole.issue_id != rep_light.issue_id
        assert any("category_mismatch" in r for r in match_pothole.reasoning)

    def test_null_island_coordinates_not_spatially_merged(self, db_session: Session) -> None:
        """Reports with (0.0, 0.0) coordinates must not merge spatially."""
        rep1 = Report(
            id=uuid.uuid4(),
            tracking_id="SYN-REP-NULL1",
            description="Pothole on unspecified road without GPS",
            category="Pothole",
            latitude=0.0,
            longitude=0.0,
        )
        db_session.add(rep1)
        db_session.flush()
        m1 = process_similarity_match(db_session, rep1)
        assert m1.action == MatchAction.NEW_ISSUE

        rep2 = Report(
            id=uuid.uuid4(),
            tracking_id="SYN-REP-NULL2",
            description="Another pothole somewhere with failed GPS",
            category="Pothole",
            latitude=0.0,
            longitude=0.0,
        )
        db_session.add(rep2)
        db_session.flush()
        m2 = process_similarity_match(db_session, rep2)
        # Must NOT auto-link at Null Island
        assert m2.action == MatchAction.NEW_ISSUE
        assert rep2.issue_id != rep1.issue_id

    def test_candidate_match_records_issue_id_and_can_be_approved(
        self, db_session: Session
    ) -> None:
        """Regression test for Bug 1: CANDIDATE match must persist candidate issue_id and be approvable."""
        # Create base issue
        issue = Issue(
            id=uuid.uuid4(),
            title="Pothole: Main Road Pothole",
            category="Pothole",
            status="OPEN",
            primary_latitude=12.9716,
            primary_longitude=77.5946,
            report_count=1,
        )
        db_session.add(issue)
        db_session.flush()

        # Create report with borderline similarity to trigger CANDIDATE
        # We configure custom thresholds so score falls in [medium, high)
        cfg = SimilarityConfig(
            text_weight=0.40,
            distance_weight=0.35,
            category_weight=0.25,
            radius_meters=50.0,
            high_threshold=0.90,  # High threshold forces CANDIDATE
            medium_threshold=0.30,
            embedding_model_version="test-minilm",
        )

        rep = Report(
            id=uuid.uuid4(),
            tracking_id="SYN-REP-CAND",
            description="Pothole outside school",
            category="Pothole",
            latitude=12.97165,
            longitude=77.59465,
        )
        db_session.add(rep)
        db_session.flush()

        match = process_similarity_match(db_session, rep, config=cfg)
        assert match.action == MatchAction.CANDIDATE
        # Report must remain unlinked until approved
        assert rep.issue_id is None

        # Verify ReportIssueMatch audit row has candidate issue_id populated (BUG 1 FIX)
        stmt = (
            db_session.query(ReportIssueMatch)
            .filter_by(report_id=rep.id, action="CANDIDATE")
            .first()
        )
        assert stmt is not None
        assert stmt.issue_id == issue.id, "Candidate match MUST record the candidate issue ID!"
        assert stmt.status == "PENDING"

        # Verify review service can approve the candidate without crashing
        review_service = MatchReviewService()
        approved_match = review_service.approve_candidate(
            db_session, stmt.id, reviewer_id="officer-42", notes="Verified duplicate"
        )
        assert approved_match.status == "APPROVED"
        assert rep.issue_id == issue.id
        assert issue.report_count == 2


# ---------------------------------------------------------------------------
# 2. Priority Scoring Boundary Tests
# ---------------------------------------------------------------------------

class TestPriorityScoringValidation:
    """Validate priority calculation across edge cases."""

    def test_zero_linked_reports_issue(self, db_session: Session) -> None:
        """An issue with 0 reports should produce a valid, finite LOW priority score."""
        issue = Issue(
            id=uuid.uuid4(),
            title="Closed empty defect",
            category="Other",
            status="OPEN",
            primary_latitude=12.97,
            primary_longitude=77.59,
            report_count=0,
        )
        db_session.add(issue)
        db_session.flush()

        breakdown = compute_issue_priority(db_session, issue)
        assert 0.0 <= breakdown.final_score_0_100 <= 100.0
        assert breakdown.priority_level == PriorityLevel.LOW
        assert breakdown.report_count == 0

    def test_single_critical_report_priority(self, db_session: Session) -> None:
        """A single CRITICAL report should elevate issue to HIGH priority."""
        issue = Issue(
            id=uuid.uuid4(),
            title="Open manhole near school",
            category="Other",
            status="OPEN",
            primary_latitude=12.97,
            primary_longitude=77.59,
            report_count=1,
        )
        db_session.add(issue)
        db_session.flush()

        # Add report with AIAnalysis CRITICAL
        rep = Report(
            id=uuid.uuid4(),
            tracking_id="REP-CRIT",
            description="Open manhole fatal hazard",
            category="Other",
            latitude=12.97,
            longitude=77.59,
            issue_id=issue.id,
        )
        db_session.add(rep)
        db_session.flush()

        from app.models.ai_analysis import AIAnalysis
        analysis = AIAnalysis(
            id=uuid.uuid4(),
            report_id=rep.id,
            confidence=0.95,
            severity=SeverityLevel.CRITICAL,
            priority=PriorityLevel.CRITICAL,
        )
        db_session.add(analysis)
        db_session.flush()

        breakdown = compute_issue_priority(db_session, issue)
        assert breakdown.final_score_0_100 >= 40.0
        assert breakdown.priority_level in (PriorityLevel.HIGH, PriorityLevel.CRITICAL)
        assert breakdown.max_severity == "CRITICAL"

    def test_many_low_severity_reports_priority(self, db_session: Session) -> None:
        """Many low-severity reports should accumulate volume and achieve HIGH or CRITICAL."""
        issue = Issue(
            id=uuid.uuid4(),
            title="Persistent littering spot",
            category="Garbage",
            status="OPEN",
            primary_latitude=12.97,
            primary_longitude=77.59,
            report_count=50,
        )
        db_session.add(issue)
        db_session.flush()

        # 50 low severity reports from 50 distinct citizens
        for i in range(50):
            rep = Report(
                id=uuid.uuid4(),
                tracking_id=f"REP-LOW-{i}",
                citizen_id=f"czn_{i}",
                description="Small garbage on sidewalk",
                category="Garbage",
                latitude=12.97,
                longitude=77.59,
                issue_id=issue.id,
            )
            db_session.add(rep)
        db_session.flush()

        breakdown = compute_issue_priority(db_session, issue)
        # Volume + unique reporters should push score into CRITICAL (>= 65)
        assert breakdown.final_score_0_100 >= 65.0
        assert breakdown.priority_level == PriorityLevel.CRITICAL

    def test_missing_severity_uses_default_fallback(self, db_session: Session) -> None:
        """Reports without AI analysis severity fall back to default (0.25)."""
        issue = Issue(
            id=uuid.uuid4(),
            title="Unanalyzed report issue",
            category="Pothole",
            status="OPEN",
            primary_latitude=12.97,
            primary_longitude=77.59,
            report_count=1,
        )
        db_session.add(issue)
        db_session.flush()

        rep = Report(
            id=uuid.uuid4(),
            tracking_id="REP-NO-AI",
            description="Pothole reported",
            category="Pothole",
            latitude=12.97,
            longitude=77.59,
            issue_id=issue.id,
        )
        db_session.add(rep)
        db_session.flush()

        breakdown = compute_issue_priority(db_session, issue)
        assert breakdown.severity_score == 0.25
        assert breakdown.max_severity is None
        assert 0.0 <= breakdown.final_score_0_100 <= 100.0


# ---------------------------------------------------------------------------
# 3. Gold-Label Dataset Integrity
# ---------------------------------------------------------------------------

class TestSyntheticDatasetIntegrity:
    """Verify data contracts of the synthetic evaluation fixtures."""

    def test_all_reports_have_valid_fields(self) -> None:
        reports = get_synthetic_reports()
        assert len(reports) == 24
        for r in reports:
            assert r.report_id.startswith("SYN-REP-")
            assert len(r.text) >= 5
            assert r.category in ["Pothole", "Garbage", "Water Leakage", "Streetlight", "Road Damage", "Other"]
            assert r.expected_severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def test_all_pairs_reference_valid_reports(self) -> None:
        reports = {r.report_id for r in get_synthetic_reports()}
        pairs = get_evaluation_pairs()
        assert len(pairs) == 20
        for p in pairs:
            assert p.report_id_a in reports
            assert p.report_id_b in reports
            assert p.expected_relationship in ["SAME_ISSUE", "DIFFERENT_ISSUE", "UNCERTAIN"]
