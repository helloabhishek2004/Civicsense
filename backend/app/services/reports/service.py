import datetime
import uuid

from sqlalchemy.orm import Session

from app.core.errors import EntityNotFoundError
from app.core.logging import get_logger
from app.models.ai_job import AIJobEvent
from app.models.enums import AIProcessingStage, PriorityLevel, ReportStatus, VerificationDecision
from app.models.report import Report
from app.models.verification import Verification
from app.repositories.report_repo import report_repository
from app.schemas.report import ReportCreate
from app.schemas.verification import VerificationCreate
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
        self,
        db: Session,
        identifier: str | uuid.UUID,
        new_status: ReportStatus,
        department: str | None = None,
        assigned_officer: str | None = None,
        priority: PriorityLevel | None = None,
        reason: str | None = None,
        notes: str | None = None,
        actor: str | None = None,
    ) -> Report:
        """Safely transition a report to a new lifecycle state."""
        report = self.get_report(db, str(identifier))

        # Validate transition against the state machine
        ReportLifecycleManager.validate_transition(report.status, new_status)

        old_status = report.status
        updated_report = self.repo.update_status(
            db,
            report,
            new_status,
            department=department,
            assigned_officer=assigned_officer,
            priority=priority,
        )
        logger.info(
            "Report %s transitioned: %s -> %s by actor=%s (dept=%s, priority=%s)",
            report.tracking_id,
            old_status.value,
            new_status.value,
            actor or "authorized_officer",
            department,
            priority.value if priority else None,
        )
        return updated_report

    def verify_report(
        self,
        db: Session,
        identifier: str | uuid.UUID,
        payload: VerificationCreate,
    ) -> Report:
        """Process human reviewer verification decision."""
        report = self.get_report(db, str(identifier))

        verification = Verification(
            report_id=report.id,
            reviewer_id=payload.reviewer_id,
            decision=payload.decision,
            verified_category=payload.verified_category,
            verified_severity=payload.verified_severity,
            notes=payload.notes,
        )
        db.add(verification)

        # Transition status based on decision where applicable
        if payload.decision in (VerificationDecision.CONFIRMED, VerificationDecision.CORRECTED):
            if ReportLifecycleManager.is_valid_transition(report.status, ReportStatus.VERIFIED):
                self.repo.update_status(db, report, ReportStatus.VERIFIED)
        elif payload.decision in (VerificationDecision.REJECTED, VerificationDecision.DUPLICATE):
            if ReportLifecycleManager.is_valid_transition(report.status, ReportStatus.CLOSED):
                self.repo.update_status(db, report, ReportStatus.CLOSED)

        # Complete pending AI reviews and log human review audit events
        now = datetime.datetime.now(datetime.UTC)
        for job in report.ai_jobs:
            if job.review_required and not job.review_completed:
                job.review_completed = True
                job.current_stage = AIProcessingStage.COMPLETED
                db.add(
                    AIJobEvent(
                        job_id=job.id,
                        report_id=report.id,
                        stage=AIProcessingStage.HUMAN_REVIEW,
                        status="COMPLETED",
                        message=(
                            f"Human review completed: verdict '{payload.decision.value}' "
                            f"by {payload.reviewer_id}."
                        ),
                        metadata_json={
                            "decision": payload.decision.value,
                            "reviewer_id": payload.reviewer_id,
                            "notes": payload.notes,
                            "verified_category": (
                                payload.verified_category.value
                                if hasattr(payload.verified_category, "value")
                                else (
                                    str(payload.verified_category)
                                    if payload.verified_category
                                    else None
                                )
                            ),
                            "verified_severity": (
                                payload.verified_severity.value
                                if hasattr(payload.verified_severity, "value")
                                else (
                                    str(payload.verified_severity)
                                    if payload.verified_severity
                                    else None
                                )
                            ),
                        },
                        started_at=now,
                        completed_at=now,
                        duration_ms=0,
                    )
                )
                db.add(
                    AIJobEvent(
                        job_id=job.id,
                        report_id=report.id,
                        stage=AIProcessingStage.COMPLETED,
                        status="COMPLETED",
                        message=(
                            "AI pipeline concluded after human verification "
                            f"({payload.decision.value})."
                        ),
                        metadata_json={
                            "decision": payload.decision.value,
                            "final_category": (
                                payload.verified_category.value
                                if hasattr(payload.verified_category, "value")
                                else (
                                    str(payload.verified_category)
                                    if payload.verified_category
                                    else (
                                        report.ai_analyses[0].predicted_category
                                        if report.ai_analyses
                                        else None
                                    )
                                )
                            ),
                        },
                        started_at=now,
                        completed_at=now,
                        duration_ms=0,
                    )
                )

        db.commit()
        return self.get_report(db, str(report.id))


report_service = ReportService()
