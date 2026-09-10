import uuid

from sqlalchemy.orm import Session

from app.models.ai_analysis import AIAnalysis
from app.models.enums import (
    EvidenceType,
    PriorityLevel,
    ReportStatus,
    SeverityLevel,
    VerificationDecision,
)
from app.models.evidence import Evidence
from app.models.issue import Issue
from app.models.model_version import ModelVersion
from app.models.report import Report
from app.models.resolution import Resolution
from app.models.verification import Verification


def test_issue_multiple_reports_relationship(db_session: Session) -> None:
    """Verify that multiple Reports can map to one Issue (Report != Issue)."""
    # 1. Create a civic Issue
    issue = Issue(
        id=uuid.uuid4(),
        title="Pothole Cluster on Main Road",
        category="pothole",
        primary_latitude=12.9716,
        primary_longitude=77.5946,
        report_count=2,
    )
    db_session.add(issue)
    db_session.commit()

    # 2. Create two distinct citizen reports linked to this Issue
    report1 = Report(
        id=uuid.uuid4(),
        tracking_id="REP-202609-TEST01",
        status=ReportStatus.SUBMITTED,
        latitude=12.9715,
        longitude=77.5947,
        description="First citizen reporting the pothole",
        issue_id=issue.id,
    )
    report2 = Report(
        id=uuid.uuid4(),
        tracking_id="REP-202609-TEST02",
        status=ReportStatus.SUBMITTED,
        latitude=12.9717,
        longitude=77.5945,
        description="Second citizen reporting same pothole with water in it",
        issue_id=issue.id,
    )
    db_session.add_all([report1, report2])
    db_session.commit()

    # 3. Verify relationships
    db_session.refresh(issue)
    assert len(issue.reports) == 2
    tracking_ids = {r.tracking_id for r in issue.reports}
    assert "REP-202609-TEST01" in tracking_ids
    assert "REP-202609-TEST02" in tracking_ids


def test_evidence_and_ai_provenance_persistence(db_session: Session) -> None:
    """Verify evidence preservation and AI analysis with model provenance tracking."""
    # 1. Create Report
    report = Report(
        id=uuid.uuid4(),
        tracking_id="REP-202609-PROV01",
        status=ReportStatus.SUBMITTED,
        latitude=12.9716,
        longitude=77.5946,
        description="Drainage overflow",
    )
    db_session.add(report)
    db_session.commit()

    # 2. Add raw evidence
    evidence = Evidence(
        id=uuid.uuid4(),
        report_id=report.id,
        evidence_type=EvidenceType.IMAGE,
        storage_uri="evidence/raw_water_01.png",
        file_hash="abc123hash",
        mime_type="image/png",
        file_size_bytes=1048576,
    )
    db_session.add(evidence)

    # 3. Add model provenance
    model_ver = ModelVersion(
        id=uuid.uuid4(),
        model_name="civicsense-multimodal",
        model_version="v0.1.0-alpha",
        preprocessing_version="prep-v1",
        embedding_model="dinov2-base",
        embedding_version="v1",
    )
    db_session.add(model_ver)
    db_session.commit()

    # 4. Attach AIAnalysis
    ai_analysis = AIAnalysis(
        id=uuid.uuid4(),
        report_id=report.id,
        model_version_id=model_ver.id,
        predicted_category="water_accumulation",
        confidence=0.94,
        severity=SeverityLevel.HIGH,
        priority=PriorityLevel.HIGH,
        evidence_agreement=0.91,
        review_required=False,
    )
    db_session.add(ai_analysis)
    db_session.commit()

    # 5. Query and assert
    db_session.refresh(report)
    assert len(report.evidences) == 1
    assert report.evidences[0].storage_uri == "evidence/raw_water_01.png"
    assert len(report.ai_analyses) == 1
    assert report.ai_analyses[0].model_version is not None
    assert report.ai_analyses[0].model_version.model_name == "civicsense-multimodal"
    assert report.ai_analyses[0].confidence == 0.94
    assert report.ai_analyses[0].severity == SeverityLevel.HIGH


def test_verification_and_resolution_tracking(db_session: Session) -> None:
    """Verify human verification on report and resolution tracking on issue."""
    issue = Issue(
        id=uuid.uuid4(),
        title="Broken Signpost",
        category="damaged_infrastructure",
        primary_latitude=13.0,
        primary_longitude=80.0,
    )
    db_session.add(issue)
    db_session.commit()

    report = Report(
        id=uuid.uuid4(),
        tracking_id="REP-202609-VER01",
        status=ReportStatus.VERIFIED,
        latitude=13.0,
        longitude=80.0,
        description="Signpost bent backwards",
        issue_id=issue.id,
    )
    db_session.add(report)
    db_session.commit()

    # Verification verdict
    verification = Verification(
        id=uuid.uuid4(),
        report_id=report.id,
        reviewer_id="reviewer-alice",
        decision=VerificationDecision.CONFIRMED,
        verified_category="damaged_infrastructure",
        verified_severity=SeverityLevel.MEDIUM,
        notes="Confirmed physical damage to municipal sign",
    )
    db_session.add(verification)

    # Resolution
    resolution = Resolution(
        id=uuid.uuid4(),
        issue_id=issue.id,
        resolver_notes="Signpost replaced and straightened",
        resolution_verified=True,
        verified_by="supervisor-bob",
    )
    db_session.add(resolution)
    db_session.commit()

    db_session.refresh(report)
    db_session.refresh(issue)

    assert len(report.verifications) == 1
    assert report.verifications[0].decision == VerificationDecision.CONFIRMED
    assert len(issue.resolutions) == 1
    assert issue.resolutions[0].resolution_verified is True
