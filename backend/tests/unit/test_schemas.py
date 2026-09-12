import uuid

import pytest
from pydantic import ValidationError

from app.models.enums import EvidenceType, PriorityLevel, SeverityLevel
from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.common import LocationSchema
from app.schemas.evidence import EvidenceCreate
from app.schemas.report import ReportCreate


def test_valid_location_schema() -> None:
    """Valid coordinates must pass validation."""
    loc = LocationSchema(latitude=13.0827, longitude=80.2707, address_hint="Anna Salai")
    assert loc.latitude == 13.0827
    assert loc.longitude == 80.2707


def test_invalid_latitude_raises_validation_error() -> None:
    """Latitude outside [-90, 90] must fail."""
    with pytest.raises(ValidationError):
        LocationSchema(latitude=90.1, longitude=0.0)

    with pytest.raises(ValidationError):
        LocationSchema(latitude=-90.1, longitude=0.0)


def test_invalid_longitude_raises_validation_error() -> None:
    """Longitude outside [-180, 180] must fail."""
    with pytest.raises(ValidationError):
        LocationSchema(latitude=0.0, longitude=180.1)

    with pytest.raises(ValidationError):
        LocationSchema(latitude=0.0, longitude=-180.1)


def test_report_create_description_length() -> None:
    """Description must be at least 3 characters."""
    loc = LocationSchema(latitude=0.0, longitude=0.0)
    with pytest.raises(ValidationError):
        ReportCreate(location=loc, description="ab")


def test_evidence_create_validation() -> None:
    """EvidenceCreate accepts valid evidence type and rejects unknown types."""
    ev = EvidenceCreate(
        evidence_type=EvidenceType.IMAGE,
        storage_uri="s3://bucket/evidence.jpg",
        file_size_bytes=1024,
    )
    assert ev.evidence_type == EvidenceType.IMAGE

    with pytest.raises(ValidationError):
        EvidenceCreate(
            evidence_type="INVALID_TYPE",
            storage_uri="s3://bucket/test.jpg",
        )


def test_ai_analysis_schema_separate_fields() -> None:
    """AIAnalysisRead schema enforces separation of confidence, severity, and priority."""
    import datetime

    analysis = AIAnalysisRead(
        id=uuid.uuid4(),
        report_id=uuid.uuid4(),
        predicted_category="pothole",
        confidence=0.92,
        severity=SeverityLevel.HIGH,
        priority=PriorityLevel.CRITICAL,
        evidence_agreement=0.88,
        review_required=True,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    assert analysis.confidence == 0.92
    assert analysis.severity == SeverityLevel.HIGH
    assert analysis.priority == PriorityLevel.CRITICAL
    assert analysis.review_required is True


def test_utc_timestamp_serialization() -> None:
    """Ensure ReportRead and AIAnalysisRead always serialize timestamps with UTC Z suffix."""
    import datetime

    from app.models.enums import ReportStatus
    from app.schemas.report import ReportRead

    # Test with naive datetime (e.g., loaded from SQLite / DB)
    naive_dt = datetime.datetime(2026, 9, 12, 10, 7, 4, 321792)
    report = ReportRead(
        id=uuid.uuid4(),
        tracking_id="REP-TEST-123",
        status=ReportStatus.SUBMITTED,
        latitude=8.52,
        longitude=76.93,
        description="Pothole test",
        created_at=naive_dt,
        updated_at=naive_dt,
    )

    # In Python, datetime object is normalized to aware UTC
    assert report.created_at.tzinfo == datetime.UTC
    assert report.updated_at.tzinfo == datetime.UTC

    # In JSON serialization, must end with Z
    dumped = report.model_dump(mode="json")
    assert dumped["created_at"] == "2026-09-12T10:07:04.321792Z"
    assert dumped["updated_at"] == "2026-09-12T10:07:04.321792Z"

    json_str = report.model_dump_json()
    assert '"created_at":"2026-09-12T10:07:04.321792Z"' in json_str
