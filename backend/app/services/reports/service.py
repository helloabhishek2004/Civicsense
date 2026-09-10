import uuid

from sqlalchemy.orm import Session

from app.core.errors import EntityNotFoundError
from app.core.logging import get_logger
from app.models.enums import ReportStatus
from app.models.report import Report
from app.repositories.report_repo import report_repository
from app.schemas.report import ReportCreate
from app.services.reports.lifecycle import ReportLifecycleManager

logger = get_logger(__name__)


class ReportService:
    """Domain service for managing citizen reports and lifecycle transitions."""

    def __init__(self) -> None:
        self.repo = report_repository

    def submit_report(self, db: Session, schema: ReportCreate) -> Report:
        """Process and persist a citizen report submission."""
        logger.info(
            "Ingesting new citizen report: desc_len=%d evidences=%d",
            len(schema.description),
            len(schema.evidence),
        )
        report = self.repo.create(db, schema)
        logger.info(
            "Report created successfully: id=%s tracking_id=%s status=%s",
            report.id,
            report.tracking_id,
            report.status.value,
        )
        return report

    def get_report(self, db: Session, identifier: str) -> Report:
        """Fetch report by UUID or tracking ID."""
        # Try UUID first
        try:
            report_uuid = uuid.UUID(identifier)
            report = self.repo.get_by_id_with_relations(db, report_uuid)
            if report:
                return report
        except ValueError:
            pass

        # Fallback to human-readable tracking_id lookup
        report = self.repo.get_by_tracking_id(db, identifier)
        if not report:
            raise EntityNotFoundError("Report", identifier)
        return report

    def list_reports(self, db: Session, skip: int = 0, limit: int = 20) -> tuple[list[Report], int]:
        """Fetch paginated list of reports."""
        return self.repo.list_reports(db, skip=skip, limit=limit)

    def transition_status(
        self, db: Session, report_id: uuid.UUID, new_status: ReportStatus
    ) -> Report:
        """Safely transition a report to a new lifecycle state."""
        report = self.repo.get_by_id_with_relations(db, report_id)
        if not report:
            raise EntityNotFoundError("Report", report_id)

        # Validate transition against the state machine
        ReportLifecycleManager.validate_transition(report.status, new_status)

        old_status = report.status
        updated_report = self.repo.update_status(db, report, new_status)
        logger.info(
            "Report %s transitioned: %s -> %s",
            report.tracking_id,
            old_status.value,
            new_status.value,
        )
        return updated_report


report_service = ReportService()
