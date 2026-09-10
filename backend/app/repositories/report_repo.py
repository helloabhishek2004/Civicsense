import datetime
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import ReportStatus
from app.models.evidence import Evidence
from app.models.report import Report
from app.repositories.base import BaseRepository
from app.schemas.report import ReportCreate


def generate_tracking_id() -> str:
    """Generate human-readable report tracking ID, e.g. REP-202609-A1B2C3."""
    now = datetime.datetime.now(datetime.UTC)
    month_prefix = now.strftime("%Y%m")
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"REP-{month_prefix}-{unique_suffix}"


class ReportRepository(BaseRepository[Report]):
    """Data access repository for citizen reports."""

    def __init__(self) -> None:
        super().__init__(Report)

    def create(self, db: Session, schema: ReportCreate) -> Report:
        """Create a new report in SUBMITTED state with attached evidence."""
        tracking_id = generate_tracking_id()
        report_id = schema.client_report_id or uuid.uuid4()

        report = Report(
            id=report_id,
            tracking_id=tracking_id,
            citizen_id=schema.citizen_id,
            status=ReportStatus.SUBMITTED,
            latitude=schema.location.latitude,
            longitude=schema.location.longitude,
            address_hint=schema.location.address_hint,
            description=schema.description,
        )

        for ev in schema.evidence:
            evidence_model = Evidence(
                report_id=report.id,
                evidence_type=ev.evidence_type,
                storage_uri=ev.storage_uri,
                file_hash=ev.file_hash,
                mime_type=ev.mime_type,
                file_size_bytes=ev.file_size_bytes,
                metadata_json=ev.metadata_json,
            )
            report.evidences.append(evidence_model)

        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    def get_by_id_with_relations(self, db: Session, report_id: uuid.UUID) -> Report | None:
        """Fetch report with eagerly loaded relations."""
        stmt = (
            select(Report)
            .options(
                joinedload(Report.evidences),
                joinedload(Report.ai_analyses),
                joinedload(Report.verifications),
            )
            .where(Report.id == report_id)
        )
        return db.scalars(stmt).unique().first()

    def get_by_tracking_id(self, db: Session, tracking_id: str) -> Report | None:
        """Fetch report by human-readable tracking ID."""
        stmt = (
            select(Report)
            .options(
                joinedload(Report.evidences),
                joinedload(Report.ai_analyses),
                joinedload(Report.verifications),
            )
            .where(Report.tracking_id == tracking_id)
        )
        return db.scalars(stmt).unique().first()

    def list_reports(self, db: Session, skip: int = 0, limit: int = 20) -> tuple[list[Report], int]:
        """List reports sorted descending by creation time with total count."""
        count_stmt = select(func.count()).select_from(Report)
        total = db.scalar(count_stmt) or 0

        stmt = (
            select(Report)
            .options(
                joinedload(Report.evidences),
                joinedload(Report.ai_analyses),
                joinedload(Report.verifications),
            )
            .order_by(desc(Report.created_at))
            .offset(skip)
            .limit(limit)
        )
        items = list(db.scalars(stmt).unique().all())
        return items, total

    def update_status(self, db: Session, report: Report, new_status: ReportStatus) -> Report:
        """Update report status and commit timestamp."""
        report.status = new_status
        report.updated_at = datetime.datetime.now(datetime.UTC)
        db.commit()
        db.refresh(report)
        return report


report_repository = ReportRepository()
