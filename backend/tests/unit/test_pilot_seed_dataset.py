"""Unit tests for the CivicSense synthetic pilot dataset and seeding integrity."""

from sqlalchemy.orm import Session

from app.evaluation.pilot_seed_dataset import (
    PILOT_ISSUES,
    PILOT_MATCHES,
    PILOT_REPORTS,
    generate_pilot_dataset_dict,
    seed_database,
)
from app.models.issue import Issue
from app.models.report import Report
from app.models.report_issue_match import ReportIssueMatch


class TestPilotSeedDataset:
    def test_dataset_specification_counts(self) -> None:
        """Verify the pilot dataset satisfies requirements: 40 reports, 12 issues, 10 matches."""
        assert len(PILOT_REPORTS) == 40
        assert len(PILOT_ISSUES) == 12
        assert len(PILOT_MATCHES) == 10

    def test_dataset_categories_and_severities(self) -> None:
        """Verify diverse categories and severity representations."""
        categories = {r.category for r in PILOT_REPORTS}
        expected = {
            "Pothole",
            "Garbage",
            "Water Leakage",
            "Broken Streetlight",
            "Damaged Footpath",
            "Open Manhole",
            "Fallen Tree",
            "Drainage Blockage",
            "Traffic Signal Failure",
            "Other",
        }
        assert expected.issubset(categories)

        severities = {r.severity for r in PILOT_REPORTS}
        assert {"CRITICAL", "HIGH", "MEDIUM", "LOW"}.issubset(severities)

    def test_zero_real_pii(self) -> None:
        """Ensure all citizen contacts are strictly synthetic demo fixtures."""
        for r in PILOT_REPORTS:
            assert "Demo Citizen" in r.citizen_name
            assert r.citizen_email.endswith(".synthetic")
            assert r.citizen_phone.startswith("+91-98765")

    def test_matches_status_distribution(self) -> None:
        """Verify presence of pending, rejected, and candidate actions."""
        statuses = {m.status for m in PILOT_MATCHES}
        assert "PENDING" in statuses
        assert "REJECTED" in statuses
        pending_matches = [m for m in PILOT_MATCHES if m.status == "PENDING"]
        assert len(pending_matches) == 6

    def test_generate_pilot_dataset_dict(self) -> None:
        """Verify serializable dict output matches expected metadata schema."""
        d = generate_pilot_dataset_dict()
        assert "metadata" in d
        assert d["metadata"]["reports_count"] == 40
        assert d["metadata"]["issues_count"] == 12
        assert d["metadata"]["matches_count"] == 10
        assert "Zero real citizen PII" in d["metadata"]["privacy_statement"]

    def test_seed_database_execution(self, db_session: Session) -> None:
        """Verify seed_database populates SQLite / DB tables with valid entities and calculated priorities."""
        summary = seed_database(db_session, reset=True)
        assert summary["issues_created"] == 12
        assert summary["reports_created"] == 40
        assert summary["matches_created"] == 10

        # Verify DB counts
        db_issues = db_session.query(Issue).all()
        assert len(db_issues) == 12

        db_reports = db_session.query(Report).all()
        assert len(db_reports) == 40

        db_matches = db_session.query(ReportIssueMatch).all()
        assert len(db_matches) == 10

        # Verify crowded issue has 8 reports and computed priority
        mg_issue = next(i for i in db_issues if "Bishop Cotton" in i.title or "MG Road" in i.title)
        assert mg_issue.report_count == 8
        assert mg_issue.priority_score is not None
        assert mg_issue.priority_score > 40.0
        assert mg_issue.priority_level == "HIGH"
