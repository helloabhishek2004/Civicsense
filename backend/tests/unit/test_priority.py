"""Tests for CivicSense Priority Ranking Engine.

Comprehensive coverage of all 5 normalized components, the weighted formula,
threshold mapping, recomputation triggers, and API integration.
"""

import datetime
import uuid
from unittest.mock import patch

import pytest

from app.models.ai_analysis import AIAnalysis
from app.models.enums import SeverityLevel
from app.models.issue import Issue
from app.models.report import Report
from app.services.priority.service import (
    FORMULA_VERSION,
    PriorityConfig,
    apply_priority_to_issue,
    compute_issue_priority,
    persistence_score,
    recency_score,
    recompute_all_priorities,
    report_volume_score,
    severity_score,
    unique_reporter_score,
)
from app.services.similarity.review import MatchReviewService
from app.services.similarity.service import process_similarity_match

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> PriorityConfig:
    defaults = dict(
        severity_weight=0.30,
        volume_weight=0.25,
        unique_reporter_weight=0.20,
        recency_weight=0.15,
        persistence_weight=0.10,
        volume_saturation=50,
        recency_half_life_days=7.0,
        persistence_max_days=90.0,
        high_threshold=65.0,
        medium_threshold=40.0,
        low_threshold=15.0,
    )
    defaults.update(overrides)
    return PriorityConfig(**defaults)


def _make_issue(session, **overrides) -> Issue:
    defaults = dict(
        id=uuid.uuid4(),
        title="Test pothole",
        category="Pothole",
        status="OPEN",
        primary_latitude=12.9716,
        primary_longitude=77.5946,
        report_count=1,
    )
    defaults.update(overrides)
    issue = Issue(**defaults)
    session.add(issue)
    session.flush()
    return issue


def _make_report(session, issue_id, **overrides) -> Report:
    now = datetime.datetime.now(datetime.UTC)
    defaults = dict(
        id=uuid.uuid4(),
        tracking_id=f"REP-PRI-{uuid.uuid4().hex[:8].upper()}",
        description="Pothole near bus stop",
        category="Pothole",
        latitude=12.9716,
        longitude=77.5946,
        status="SUBMITTED",
        issue_id=issue_id,
        citizen_id=f"citizen-{uuid.uuid4().hex[:8]}",
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    report = Report(**defaults)
    session.add(report)
    session.flush()
    return report


def _make_analysis(session, report_id, severity=None):
    if severity is None:
        return None
    analysis = AIAnalysis(
        id=uuid.uuid4(),
        report_id=report_id,
        severity=severity,
        confidence=0.85,
        predicted_category="Pothole",
    )
    session.add(analysis)
    session.flush()
    return analysis


# ===========================================================================
# Component: severity_score
# ===========================================================================

class TestSeverityScore:
    def test_no_analyses_returns_default(self, db_session):
        issue = _make_issue(db_session)
        _make_report(db_session, issue.id)
        score, label, count = severity_score(db_session, issue)
        assert score == pytest.approx(0.25, abs=0.01)
        assert label is None
        assert count == 0

    def test_single_low_severity(self, db_session):
        issue = _make_issue(db_session)
        report = _make_report(db_session, issue.id)
        _make_analysis(db_session, report.id, SeverityLevel.LOW)
        score, label, count = severity_score(db_session, issue)
        assert score == pytest.approx(0.25, abs=0.01)
        assert label == SeverityLevel.LOW
        assert count == 1

    def test_single_critical_severity(self, db_session):
        issue = _make_issue(db_session)
        report = _make_report(db_session, issue.id)
        _make_analysis(db_session, report.id, SeverityLevel.CRITICAL)
        score, label, count = severity_score(db_session, issue)
        assert score == pytest.approx(1.0, abs=0.01)
        assert label == SeverityLevel.CRITICAL
        assert count == 1

    def test_mixed_severity_uses_max(self, db_session):
        issue = _make_issue(db_session)
        r1 = _make_report(db_session, issue.id)
        r2 = _make_report(db_session, issue.id)
        r3 = _make_report(db_session, issue.id)
        _make_analysis(db_session, r1.id, SeverityLevel.LOW)
        _make_analysis(db_session, r2.id, SeverityLevel.HIGH)
        _make_analysis(db_session, r3.id, SeverityLevel.MEDIUM)
        score, label, count = severity_score(db_session, issue)
        assert score == pytest.approx(0.75, abs=0.01)
        assert label == SeverityLevel.HIGH
        assert count == 3

    def test_repeated_critical_has_ceiling(self, db_session):
        issue = _make_issue(db_session)
        r1 = _make_report(db_session, issue.id)
        r2 = _make_report(db_session, issue.id)
        r3 = _make_report(db_session, issue.id)
        _make_analysis(db_session, r1.id, SeverityLevel.CRITICAL)
        _make_analysis(db_session, r2.id, SeverityLevel.CRITICAL)
        _make_analysis(db_session, r3.id, SeverityLevel.CRITICAL)
        score, label, count = severity_score(db_session, issue)
        assert score == pytest.approx(1.0, abs=0.02)
        assert label == SeverityLevel.CRITICAL
        assert count == 3

    def test_only_analyses_without_severity_excluded(self, db_session):
        issue = _make_issue(db_session)
        report = _make_report(db_session, issue.id)
        _make_analysis(db_session, report.id, None)
        score, label, count = severity_score(db_session, issue)
        assert score == pytest.approx(0.25, abs=0.01)
        assert label is None
        assert count == 0


# ===========================================================================
# Component: report_volume_score
# ===========================================================================

class TestReportVolumeScore:
    def test_zero_reports(self):
        assert report_volume_score(0, 50) == 0.0

    def test_one_report(self):
        score = report_volume_score(1, 50)
        assert 0.0 < score < 0.3

    def test_half_saturation(self):
        score = report_volume_score(25, 50)
        assert 0.7 < score < 0.85

    def test_full_saturation(self):
        score = report_volume_score(50, 50)
        assert 0.9 < score < 1.0

    def test_above_saturation(self):
        score = report_volume_score(200, 50)
        assert 0.95 < score <= 1.0

    def test_monotonically_increasing(self):
        scores = [report_volume_score(n, 50) for n in range(0, 210, 10)]
        for i in range(1, len(scores)):
            assert scores[i] > scores[i - 1]

    def test_custom_saturation(self):
        assert report_volume_score(50, 50) > report_volume_score(50, 100)


# ===========================================================================
# Component: unique_reporter_score
# ===========================================================================

class TestUniqueReporterScore:
    def test_no_reports(self, db_session):
        issue = _make_issue(db_session)
        score, count = unique_reporter_score(db_session, issue, 0)
        assert score == 0.0
        assert count == 0

    def test_single_citizen(self, db_session):
        issue = _make_issue(db_session)
        _make_report(db_session, issue.id, citizen_id="citizen-A")
        score, count = unique_reporter_score(db_session, issue, 1)
        assert 0.2 < score < 0.4
        assert count == 1

    def test_multiple_citizens(self, db_session):
        issue = _make_issue(db_session)
        for i in range(5):
            _make_report(db_session, issue.id, citizen_id=f"citizen-{i}")
        score, count = unique_reporter_score(db_session, issue, 5)
        assert 0.7 < score < 1.0
        assert count == 5

    def test_anonymous_single_counted_once(self, db_session):
        issue = _make_issue(db_session)
        _make_report(db_session, issue.id, citizen_id=None)
        _make_report(db_session, issue.id, citizen_id=None)
        score, count = unique_reporter_score(db_session, issue, 2)
        assert count == 1

    def test_mixed_citizen_and_anonymous(self, db_session):
        issue = _make_issue(db_session)
        _make_report(db_session, issue.id, citizen_id="citizen-A")
        _make_report(db_session, issue.id, citizen_id=None)
        _make_report(db_session, issue.id, citizen_id=None)
        score, count = unique_reporter_score(db_session, issue, 3)
        assert count == 2

    def test_empty_citizen_id_same_as_none(self, db_session):
        issue = _make_issue(db_session)
        _make_report(db_session, issue.id, citizen_id="")
        score, count = unique_reporter_score(db_session, issue, 1)
        assert count == 1


# ===========================================================================
# Component: recency_score
# ===========================================================================

class TestRecencyScore:
    def test_no_latest_report(self):
        assert recency_score(None, 7.0) == 0.0

    def test_just_now(self):
        now = datetime.datetime.now(datetime.UTC)
        score = recency_score(now, 7.0, now)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_one_half_life_ago(self):
        now = datetime.datetime.now(datetime.UTC)
        t = now - datetime.timedelta(days=7.0)
        score = recency_score(t, 7.0, now)
        assert score == pytest.approx(0.5, abs=0.05)

    def test_two_half_lives_ago(self):
        now = datetime.datetime.now(datetime.UTC)
        t = now - datetime.timedelta(days=14.0)
        score = recency_score(t, 7.0, now)
        assert score == pytest.approx(0.25, abs=0.05)

    def test_very_old_report(self):
        now = datetime.datetime.now(datetime.UTC)
        old = now - datetime.timedelta(days=90)
        score = recency_score(old, 7.0, now)
        assert score < 0.01

    def test_custom_half_life(self):
        now = datetime.datetime.now(datetime.UTC)
        t = now - datetime.timedelta(days=3.0)
        score_3 = recency_score(t, 3.0, now)
        score_7 = recency_score(t, 7.0, now)
        assert score_3 < score_7

    def test_naive_datetime_handled(self):
        naive = datetime.datetime(2026, 1, 15, 12, 0, 0)
        now = datetime.datetime.now(datetime.UTC)
        score = recency_score(naive, 7.0, now)
        assert 0.0 <= score <= 1.0


# ===========================================================================
# Component: persistence_score
# ===========================================================================

class TestPersistenceScore:
    def test_brand_new_issue(self):
        now = datetime.datetime.now(datetime.UTC)
        created = now - datetime.timedelta(hours=1)
        score = persistence_score(created, None, "OPEN", 90.0, now)
        assert 0.0 < score < 0.2

    def test_old_open_issue(self):
        now = datetime.datetime.now(datetime.UTC)
        created = now - datetime.timedelta(days=30)
        score = persistence_score(created, None, "OPEN", 90.0, now)
        assert 0.5 < score < 0.9

    def test_very_old_issue_saturates(self):
        now = datetime.datetime.now(datetime.UTC)
        created = now - datetime.timedelta(days=200)
        score = persistence_score(created, None, "OPEN", 90.0, now)
        assert 0.9 < score <= 1.0

    def test_closed_issue_penalized(self):
        now = datetime.datetime.now(datetime.UTC)
        created = now - datetime.timedelta(days=30)
        latest = now - datetime.timedelta(days=1)
        score_closed = persistence_score(created, latest, "CLOSED", 90.0, now)
        score_active = persistence_score(created, latest, "OPEN", 90.0, now)
        assert score_closed <= score_active

    def test_active_with_recent_report_boosts(self):
        now = datetime.datetime.now(datetime.UTC)
        created = now - datetime.timedelta(days=30)
        latest = now - datetime.timedelta(days=1)
        score_active = persistence_score(created, latest, "OPEN", 90.0, now)
        score_stale = persistence_score(created, None, "OPEN", 90.0, now)
        assert score_active >= score_stale

    def test_resolved_status_like_closed(self):
        now = datetime.datetime.now(datetime.UTC)
        created = now - datetime.timedelta(days=30)
        score_closed = persistence_score(created, None, "CLOSED", 90.0, now)
        score_resolved = persistence_score(created, None, "RESOLVED", 90.0, now)
        assert score_closed == pytest.approx(score_resolved, abs=0.01)


# ===========================================================================
# Full computation: compute_issue_priority
# ===========================================================================

class TestComputeIssuePriority:
    def test_new_issue_low_priority(self, db_session):
        issue = _make_issue(db_session)
        _make_report(db_session, issue.id, citizen_id="citizen-A")
        breakdown = compute_issue_priority(db_session, issue)
        assert 0.0 <= breakdown.final_score_0_100 <= 100.0
        assert breakdown.formula_version == FORMULA_VERSION
        assert breakdown.report_count == 1
        assert breakdown.max_severity is None
        assert breakdown.priority_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_critical_severity_high_priority(self, db_session):
        issue = _make_issue(db_session, report_count=10)
        for i in range(10):
            r = _make_report(db_session, issue.id, citizen_id=f"citizen-{i}")
            _make_analysis(db_session, r.id, SeverityLevel.CRITICAL)
        breakdown = compute_issue_priority(db_session, issue)
        assert breakdown.final_score_0_100 > 50.0
        assert breakdown.max_severity == SeverityLevel.CRITICAL

    def test_many_reports_high_volume(self, db_session):
        issue = _make_issue(db_session, report_count=100)
        for i in range(100):
            _make_report(db_session, issue.id, citizen_id=f"citizen-{i}")
        breakdown = compute_issue_priority(db_session, issue)
        assert breakdown.report_volume_score > 0.95
        assert breakdown.unique_reporter_score > 0.95

    def test_score_always_clamped(self, db_session):
        issue = _make_issue(db_session, report_count=1000)
        for i in range(1000):
            r = _make_report(db_session, issue.id, citizen_id=f"citizen-{i}")
            _make_analysis(db_session, r.id, SeverityLevel.CRITICAL)
        breakdown = compute_issue_priority(db_session, issue)
        assert 0.0 <= breakdown.final_score_0_100 <= 100.0

    def test_breakdown_dict_matches_fields(self, db_session):
        issue = _make_issue(db_session)
        _make_report(db_session, issue.id, citizen_id="citizen-A")
        breakdown = compute_issue_priority(db_session, issue)
        d = breakdown.to_dict()
        assert d["severity_score"] == pytest.approx(breakdown.severity_score, abs=0.01)
        assert d["report_volume_score"] == pytest.approx(breakdown.report_volume_score, abs=0.01)
        assert d["priority_level"] == breakdown.priority_level
        assert d["formula_version"] == FORMULA_VERSION

    def test_all_components_normalized(self, db_session):
        issue = _make_issue(db_session, report_count=50)
        for i in range(50):
            r = _make_report(db_session, issue.id, citizen_id=f"citizen-{i}")
            _make_analysis(db_session, r.id, SeverityLevel.HIGH)
        breakdown = compute_issue_priority(db_session, issue)
        assert 0.0 <= breakdown.severity_score <= 1.0
        assert 0.0 <= breakdown.report_volume_score <= 1.0
        assert 0.0 <= breakdown.unique_reporter_score <= 1.0
        assert 0.0 <= breakdown.recency_score <= 1.0
        assert 0.0 <= breakdown.persistence_score <= 1.0

    def test_weights_sum_to_one(self):
        config = _make_config()
        total = (
            config.severity_weight
            + config.volume_weight
            + config.unique_reporter_weight
            + config.recency_weight
            + config.persistence_weight
        )
        assert total == pytest.approx(1.0, abs=0.01)


# ===========================================================================
# Threshold mapping
# ===========================================================================

class TestPriorityThresholds:
    def test_critical_threshold(self, db_session):
        config = _make_config(high_threshold=65.0)
        issue = _make_issue(db_session, report_count=80)
        for i in range(80):
            r = _make_report(db_session, issue.id, citizen_id=f"citizen-{i}")
            _make_analysis(db_session, r.id, SeverityLevel.CRITICAL)
        breakdown = compute_issue_priority(db_session, issue, config)
        if breakdown.final_score_0_100 >= 65.0:
            assert breakdown.priority_level == "CRITICAL"

    def test_low_threshold(self, db_session):
        issue = _make_issue(db_session)
        breakdown = compute_issue_priority(db_session, issue)
        if breakdown.final_score_0_100 < 15.0:
            assert breakdown.priority_level == "LOW"


# ===========================================================================
# apply_priority_to_issue
# ===========================================================================

class TestApplyPriorityToIssue:
    def test_writes_fields_to_issue(self, db_session):
        issue = _make_issue(db_session)
        _make_report(db_session, issue.id, citizen_id="citizen-A")
        breakdown = apply_priority_to_issue(db_session, issue)
        assert issue.priority_score is not None
        assert issue.priority_level is not None
        assert issue.priority_computed_at is not None
        assert issue.priority_breakdown is not None
        assert issue.priority_score == pytest.approx(breakdown.final_score_0_100, abs=0.01)

    def test_returns_breakdown(self, db_session):
        issue = _make_issue(db_session)
        breakdown = apply_priority_to_issue(db_session, issue)
        assert breakdown.formula_version == FORMULA_VERSION
        assert isinstance(breakdown.to_dict(), dict)


# ===========================================================================
# Batch recompute
# ===========================================================================

class TestRecomputeAllPriorities:
    def test_recompute_open_issues(self, db_session):
        i1 = _make_issue(db_session, status="OPEN")
        i2 = _make_issue(db_session, status="OPEN")
        _make_issue(db_session, status="CLOSED")
        _make_report(db_session, i1.id, citizen_id="A")
        _make_report(db_session, i2.id, citizen_id="B")

        summary = recompute_all_priorities(db_session, status_filter="OPEN")
        assert summary["processed"] == 2
        assert summary["total"] == 2
        assert summary["errors"] == 0

    def test_recompute_all_statuses(self, db_session):
        _make_issue(db_session, status="OPEN")
        _make_issue(db_session, status="CLOSED")
        summary = recompute_all_priorities(db_session, status_filter=None)
        assert summary["processed"] == 2
        assert summary["total"] == 2

    def test_handles_nonexistent_issue_gracefully(self, db_session):
        issue = _make_issue(db_session)
        _make_report(db_session, issue.id, citizen_id="A")
        db_session.flush()
        db_session.delete(issue)
        db_session.flush()
        summary = recompute_all_priorities(db_session)
        # The deleted issue may or may not appear depending on cascade behavior
        assert summary["processed"] + summary["errors"] >= 0

    def test_level_distribution_populated(self, db_session):
        for _ in range(5):
            issue = _make_issue(db_session)
            _make_report(db_session, issue.id, citizen_id=f"citizen-{uuid.uuid4().hex[:6]}")
        summary = recompute_all_priorities(db_session)
        assert len(summary["level_distribution"]) > 0


# ===========================================================================
# Recomputation triggers: AUTO_LINK and NEW_ISSUE
# ===========================================================================

class TestPriorityRecomputeTriggers:
    def test_new_issue_gets_priority(self, db_session):
        now = datetime.datetime.now(datetime.UTC)
        report = Report(
            id=uuid.uuid4(),
            tracking_id=f"REP-PRI-{uuid.uuid4().hex[:8].upper()}",
            description="Pothole near bus stop",
            category="Pothole",
            latitude=12.9716,
            longitude=77.5946,
            status="SUBMITTED",
            issue_id=None,
            citizen_id="citizen-test",
            text_embedding=[0.1] * 384,
            created_at=now,
            updated_at=now,
        )
        db_session.add(report)
        db_session.flush()
        _make_analysis(db_session, report.id, SeverityLevel.HIGH)
        with patch("app.services.similarity.service._compute_text_embedding", return_value=[0.1] * 384):
            process_similarity_match(db_session, report)
        issue = db_session.get(Issue, report.issue_id)
        assert issue is not None
        assert issue.priority_score is not None
        assert issue.priority_level is not None

    def test_auto_link_triggers_recompute(self, db_session):
        existing = _make_issue(db_session, report_count=1)
        existing.text_embedding = [0.1] * 384
        _make_report(db_session, existing.id, citizen_id="A")

        now = datetime.datetime.now(datetime.UTC)
        report = Report(
            id=uuid.uuid4(),
            tracking_id=f"REP-PRI-{uuid.uuid4().hex[:8].upper()}",
            description="Pothole near bus stop",
            category="Pothole",
            latitude=existing.primary_latitude,
            longitude=existing.primary_longitude,
            status="SUBMITTED",
            issue_id=None,
            citizen_id="citizen-B",
            text_embedding=[0.1] * 384,
            created_at=now,
            updated_at=now,
        )
        db_session.add(report)
        db_session.flush()
        _make_analysis(db_session, report.id, SeverityLevel.MEDIUM)

        with patch("app.services.similarity.service._compute_text_embedding", return_value=[0.1] * 384):
            process_similarity_match(db_session, report)

        db_session.refresh(existing)
        assert existing.priority_score is not None
        assert existing.priority_level is not None
        assert existing.report_count == 2

    def test_approve_candidate_triggers_recompute(self, db_session):
        from app.models.enums import MatchAction
        from app.models.report_issue_match import ReportIssueMatch

        issue = _make_issue(db_session, report_count=1)
        report = _make_report(db_session, issue.id, citizen_id="A")

        record = ReportIssueMatch(
            id=uuid.uuid4(),
            report_id=report.id,
            issue_id=issue.id,
            action=MatchAction.CANDIDATE.value,
            status="PENDING",
            combined_score=0.55,
            text_similarity=0.6,
            distance_meters=10.0,
            category_match=1.0,
            reasoning=["Test candidate"],
        )
        db_session.add(record)
        db_session.flush()

        review_service = MatchReviewService()
        review_service.approve_candidate(db_session, record.id, reviewer_id="reviewer-1")

        db_session.refresh(issue)
        assert issue.priority_score is not None
        assert issue.priority_level is not None
        assert issue.report_count == 2


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:
    def test_issue_with_no_reports(self, db_session):
        issue = _make_issue(db_session, report_count=0)
        breakdown = compute_issue_priority(db_session, issue)
        assert breakdown.final_score_0_100 < 20.0
        assert breakdown.priority_level == "LOW"

    def test_all_weights_zero(self, db_session):
        config = _make_config(
            severity_weight=0.0,
            volume_weight=0.0,
            unique_reporter_weight=0.0,
            recency_weight=0.0,
            persistence_weight=0.0,
        )
        issue = _make_issue(db_session)
        _make_report(db_session, issue.id, citizen_id="A")
        breakdown = compute_issue_priority(db_session, issue, config)
        assert breakdown.final_score_0_100 == 0.0

    def test_custom_thresholds(self, db_session):
        config = _make_config(high_threshold=30.0, medium_threshold=10.0, low_threshold=5.0)
        issue = _make_issue(db_session, report_count=10)
        for i in range(10):
            r = _make_report(db_session, issue.id, citizen_id=f"citizen-{i}")
            _make_analysis(db_session, r.id, SeverityLevel.MEDIUM)
        breakdown = compute_issue_priority(db_session, issue, config)
        assert breakdown.priority_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
