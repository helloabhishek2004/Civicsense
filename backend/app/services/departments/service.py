import datetime
import uuid

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import EntityNotFoundError, InvalidStateTransitionError
from app.core.logging import get_logger
from app.models.assignment import ReportAssignment
from app.models.department import Department
from app.models.enums import (
    AssignmentStatus,
    DepartmentRejectionReason,
    PriorityLevel,
    ReportStatus,
)
from app.models.report import Report
from app.repositories.report_repo import report_repository
from app.schemas.department import DepartmentWorkloadStats
from app.services.reports.lifecycle import ReportLifecycleManager

logger = get_logger(__name__)


class DepartmentService:
    """Domain service managing municipal departments, job assignments, and department workflows."""

    def __init__(self) -> None:
        self.report_repo = report_repository

    def list_departments(self, db: Session, active_only: bool = True) -> list[Department]:
        """Fetch list of all municipal departments ordered by name."""
        stmt = select(Department)
        if active_only:
            stmt = stmt.where(Department.is_active == True)  # noqa: E712
        stmt = stmt.order_by(Department.name.asc())
        return list(db.scalars(stmt).all())

    def get_department(self, db: Session, identifier: str | uuid.UUID) -> Department:
        """Fetch department by UUID, uppercase code, or name."""
        try:
            dept_uuid = uuid.UUID(str(identifier))
            dept = db.get(Department, dept_uuid)
            if dept:
                return dept
        except ValueError:
            pass

        # Fallback to code or name lookup
        ident_str = str(identifier).strip()
        stmt = select(Department).where(
            or_(
                Department.code == ident_str.upper(),
                Department.name.ilike(ident_str),
            )
        )
        dept = db.scalars(stmt).first()
        if not dept:
            raise EntityNotFoundError("Department", str(identifier))
        return dept

    def get_workload_stats(
        self, db: Session, identifier: str | uuid.UUID
    ) -> DepartmentWorkloadStats:
        """Calculate real-time operational workload metrics for a department."""
        dept = self.get_department(db, identifier)

        # Count reports assigned to this department
        base_filter = or_(Report.department_id == dept.id, Report.department == dept.name)

        total_assigned = db.scalar(
            select(func.count()).select_from(Report).where(base_filter)
        ) or 0

        pending_ack = db.scalar(
            select(func.count())
            .select_from(Report)
            .where(base_filter, Report.status == ReportStatus.ASSIGNED)
        ) or 0

        in_progress = db.scalar(
            select(func.count())
            .select_from(Report)
            .where(base_filter, Report.status == ReportStatus.IN_PROGRESS)
        ) or 0

        resolved = db.scalar(
            select(func.count())
            .select_from(Report)
            .where(
                base_filter,
                Report.status.in_([
                    ReportStatus.RESOLVED,
                    ReportStatus.RESOLUTION_VERIFIED,
                    ReportStatus.CLOSED,
                ]),
            )
        ) or 0

        rejected = db.scalar(
            select(func.count())
            .select_from(ReportAssignment)
            .where(
                ReportAssignment.department_id == dept.id,
                ReportAssignment.status == AssignmentStatus.REJECTED,
            )
        ) or 0

        reassignment_req = db.scalar(
            select(func.count())
            .select_from(Report)
            .where(base_filter, Report.reassignment_required == True)  # noqa: E712
        ) or 0

        return DepartmentWorkloadStats(
            department_id=dept.id,
            department_name=dept.name,
            department_code=dept.code,
            total_assigned=total_assigned,
            pending_acknowledgment=pending_ack,
            in_progress=in_progress,
            resolved=resolved,
            rejected_assignments=rejected,
            reassignment_required=reassignment_req,
        )

    def get_department_reports(
        self,
        db: Session,
        identifier: str | uuid.UUID,
        status: ReportStatus | None = None,
        priority: PriorityLevel | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Report], int]:
        """Fetch reports assigned to a department with optional status/priority filters."""
        dept = self.get_department(db, identifier)
        return self.report_repo.list_reports(
            db,
            skip=skip,
            limit=limit,
            department_id=dept.id,
            status=status,
            priority=priority,
        )

    def assign_report(
        self,
        db: Session,
        report_id: str | uuid.UUID,
        department_id: uuid.UUID | None = None,
        department_name: str | None = None,
        assigned_by: str = "Triage Officer",
        assigned_to_officer: str | None = None,
        notes: str | None = None,
    ) -> Report:
        """Assign or re-assign a report to a municipal department."""
        # Find target department
        dept_ident = department_id or department_name
        if not dept_ident:
            raise ValueError("Either department_id or department_name must be provided.")
        dept = self.get_department(db, dept_ident)

        # Lookup report
        report = self._resolve_report(db, report_id)

        # Validate lifecycle transition if not already in ASSIGNED state
        if report.status != ReportStatus.ASSIGNED:
            ReportLifecycleManager.validate_transition(report.status, ReportStatus.ASSIGNED)

        now = datetime.datetime.now(datetime.UTC)

        # Create historical assignment record
        assignment = ReportAssignment(
            id=uuid.uuid4(),
            report_id=report.id,
            department_id=dept.id,
            department_name=dept.name,
            assigned_by=assigned_by,
            assigned_to_officer=assigned_to_officer,
            status=AssignmentStatus.ASSIGNED,
            notes=notes,
            created_at=now,
        )
        db.add(assignment)

        # Update report state
        report.status = ReportStatus.ASSIGNED
        report.department_id = dept.id
        report.department = dept.name
        report.assigned_officer = assigned_to_officer
        report.reassignment_required = False
        report.updated_at = now

        db.commit()
        db.refresh(report)
        logger.info(
            "Report %s assigned to department %s (%s) by %s",
            report.tracking_id,
            dept.name,
            dept.code,
            assigned_by,
        )
        return self.report_repo.get_by_id_with_relations(db, report.id) or report

    def acknowledge_report(
        self,
        db: Session,
        report_id: str | uuid.UUID,
        assigned_to_officer: str | None = None,
        notes: str | None = None,
    ) -> Report:
        """Department acknowledges job assignment and transitions report to IN_PROGRESS."""
        report = self._resolve_report(db, report_id)

        # Must be in ASSIGNED state (or already IN_PROGRESS for idempotent ack)
        if report.status != ReportStatus.ASSIGNED and report.status != ReportStatus.IN_PROGRESS:
            raise InvalidStateTransitionError(
                from_state=report.status.value,
                to_state=ReportStatus.IN_PROGRESS.value,
                reason="Only reports in ASSIGNED status can be acknowledged by a department.",
            )

        now = datetime.datetime.now(datetime.UTC)

        # Update latest assignment record if present
        current_assignment = report.current_assignment
        if current_assignment and current_assignment.status == AssignmentStatus.ASSIGNED:
            current_assignment.status = AssignmentStatus.IN_PROGRESS
            if assigned_to_officer:
                current_assignment.assigned_to_officer = assigned_to_officer
            if notes:
                current_assignment.notes = (
                    f"{current_assignment.notes}\nAck: {notes}".strip()
                    if current_assignment.notes
                    else notes
                )

        report.status = ReportStatus.IN_PROGRESS
        if assigned_to_officer:
            report.assigned_officer = assigned_to_officer
        report.updated_at = now

        db.commit()
        db.refresh(report)
        logger.info("Report %s acknowledged by department. Status: IN_PROGRESS", report.tracking_id)
        return self.report_repo.get_by_id_with_relations(db, report.id) or report

    def complete_report(
        self,
        db: Session,
        report_id: str | uuid.UUID,
        resolver_notes: str,
        resolved_by: str | None = None,
    ) -> Report:
        """Department marks work complete with mandatory notes; moves to RESOLVED."""
        if not resolver_notes or len(resolver_notes.strip()) < 5:
            raise ValueError("Resolution notes must be at least 5 characters.")

        report = self._resolve_report(db, report_id)

        if report.status != ReportStatus.IN_PROGRESS:
            raise InvalidStateTransitionError(
                from_state=report.status.value,
                to_state=ReportStatus.RESOLVED.value,
                reason="Only reports in IN_PROGRESS status can be marked completed.",
            )

        now = datetime.datetime.now(datetime.UTC)

        current_assignment = report.current_assignment
        if current_assignment and current_assignment.status == AssignmentStatus.IN_PROGRESS:
            current_assignment.status = AssignmentStatus.COMPLETED
            current_assignment.resolved_at = now
            note_entry = f"Resolved by {resolved_by or 'Department'}: {resolver_notes}"
            current_assignment.notes = (
                f"{current_assignment.notes}\n{note_entry}".strip()
                if current_assignment.notes
                else note_entry
            )

        report.status = ReportStatus.RESOLVED
        report.updated_at = now

        db.commit()
        db.refresh(report)
        logger.info("Report %s completed by department. Status: RESOLVED", report.tracking_id)
        return self.report_repo.get_by_id_with_relations(db, report.id) or report

    def reject_report(
        self,
        db: Session,
        report_id: str | uuid.UUID,
        rejection_reason: DepartmentRejectionReason,
        notes: str,
        suggested_department: str | None = None,
    ) -> Report:
        """Department declines an assigned job.

        Transitions report from ASSIGNED back to PRIORITIZED.
        Flags reassignment_required=True.
        Preserves original department reference and logs immutable assignment rejection.
        """
        if not notes or len(notes.strip()) < 5:
            raise ValueError("Rejection notes must be at least 5 characters describing reason.")

        report = self._resolve_report(db, report_id)

        if report.status != ReportStatus.ASSIGNED:
            raise InvalidStateTransitionError(
                from_state=report.status.value,
                to_state=ReportStatus.PRIORITIZED.value,
                reason="Only reports currently in ASSIGNED status can be rejected by a department.",
            )

        now = datetime.datetime.now(datetime.UTC)

        current_assignment = report.current_assignment
        if current_assignment and current_assignment.status == AssignmentStatus.ASSIGNED:
            current_assignment.status = AssignmentStatus.REJECTED
            current_assignment.rejection_reason = rejection_reason
            current_assignment.resolved_at = now
            note_content = notes
            if suggested_department:
                note_content = f"{notes} (Suggested: {suggested_department})"
            current_assignment.notes = (
                f"{current_assignment.notes}\nRejection: {note_content}".strip()
                if current_assignment.notes
                else note_content
            )

        # Transition back to PRIORITIZED and flag reassignment needed
        # Do NOT clear report.department (preserve historical context)
        report.status = ReportStatus.PRIORITIZED
        report.reassignment_required = True
        report.updated_at = now

        db.commit()
        db.refresh(report)
        logger.info(
            "Report %s assignment rejected by department (%s: %s). Returned to PRIORITIZED.",
            report.tracking_id,
            rejection_reason.value,
            notes,
        )
        return self.report_repo.get_by_id_with_relations(db, report.id) or report

    def get_assignment_history(
        self, db: Session, report_id: str | uuid.UUID
    ) -> list[ReportAssignment]:
        """Fetch chronological assignment audit records for a report."""
        report = self._resolve_report(db, report_id)
        stmt = (
            select(ReportAssignment)
            .where(ReportAssignment.report_id == report.id)
            .order_by(desc(ReportAssignment.created_at))
        )
        return list(db.scalars(stmt).all())

    def _resolve_report(self, db: Session, identifier: str | uuid.UUID) -> Report:
        try:
            report_uuid = uuid.UUID(str(identifier))
            report = self.report_repo.get_by_id_with_relations(db, report_uuid)
            if report:
                return report
        except ValueError:
            pass

        report = self.report_repo.get_by_tracking_id(db, str(identifier))
        if not report:
            raise EntityNotFoundError("Report", str(identifier))
        return report


department_service = DepartmentService()
