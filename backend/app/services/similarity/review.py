"""Service for reviewing, approving, or rejecting CANDIDATE matches.

When a medium-confidence candidate is submitted for human review, this
service executes the decision:
  - APPROVED: links the report to the candidate issue
  - REJECTED: leaves the report unlinked (or links to a different issue)
"""

import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import EntityNotFoundError, MatchAlreadyReviewedError
from app.core.logging import get_logger
from app.models.issue import Issue
from app.models.report import Report
from app.models.report_issue_match import ReportIssueMatch

logger = get_logger(__name__)


class MatchReviewService:
    """Handles human review decisions on candidate similarity matches."""

    def approve_candidate(
        self,
        db: Session,
        match_id: uuid.UUID,
        *,
        reviewer_id: str = "system",
        notes: str | None = None,
    ) -> ReportIssueMatch:
        """Approve a PENDING candidate: link the report to the candidate issue.

        Args:
            db: Active database session.
            match_id: ID of the ReportIssueMatch to approve.
            reviewer_id: Identifier of the reviewing officer.
            notes: Optional reviewer notes.

        Returns:
            The updated ReportIssueMatch with status=APPROVED.

        Raises:
            EntityNotFoundError: If match not found or not PENDING.
        """
        record = db.get(ReportIssueMatch, match_id)
        if record is None:
            raise EntityNotFoundError("ReportIssueMatch", str(match_id))
        if record.status != "PENDING":
            raise MatchAlreadyReviewedError(match_id, record.status)
        if record.issue_id is None:
            raise ValueError(f"Match {match_id} has no candidate issue_id to approve")

        now = datetime.datetime.now(datetime.UTC)

        # Link the report to the candidate issue
        report = db.get(Report, record.report_id)
        if report is None:
            raise EntityNotFoundError("Report", str(record.report_id))

        issue = db.get(Issue, record.issue_id)
        if issue is None:
            raise EntityNotFoundError("Issue", str(record.issue_id))

        report.issue_id = issue.id
        issue.report_count += 1
        issue.updated_at = now

        # Update issue embeddings as running average (consistent with service.py)
        from app.services.similarity.service import _running_average
        if report.text_embedding:
            issue.text_embedding = _running_average(
                issue.text_embedding,
                report.text_embedding,
                issue.report_count - 1,
            )
        if report.image_embedding:
            if issue.image_embedding:
                issue.image_embedding = _running_average(
                    issue.image_embedding,
                    report.image_embedding,
                    issue.report_count - 1,
                )
            else:
                issue.image_embedding = list(report.image_embedding)
                issue.vision_model_version = report.vision_model_version

        # Mark any other PENDING matches for this report as SUPERSEDED
        self._supersede_other_pending(db, record)

        # Update the match record
        record.status = "APPROVED"
        record.reviewed_at = now
        record.reviewer_id = reviewer_id
        record.review_notes = notes
        db.flush()

        # Recompute priority after candidate approved
        try:
            from app.services.priority.service import apply_priority_to_issue
            apply_priority_to_issue(db, issue)
        except Exception:
            logger.debug("Priority recompute skipped for issue %s", issue.id)

        logger.info(
            "Candidate match APPROVED: match=%s report=%s issue=%s reviewer=%s",
            match_id, report.id, issue.id, reviewer_id,
        )
        return record

    def reject_candidate(
        self,
        db: Session,
        match_id: uuid.UUID,
        *,
        reviewer_id: str = "system",
        notes: str | None = None,
        link_to_issue_id: uuid.UUID | None = None,
    ) -> ReportIssueMatch:
        """Reject a PENDING candidate.

        Optionally links the report to a different issue if link_to_issue_id is provided.

        Args:
            db: Active database session.
            match_id: ID of the ReportIssueMatch to reject.
            reviewer_id: Identifier of the reviewing officer.
            notes: Optional reviewer notes.
            link_to_issue_id: If provided, link report to this issue instead.

        Returns:
            The updated ReportIssueMatch with status=REJECTED.

        Raises:
            EntityNotFoundError: If match not found or not PENDING.
        """
        record = db.get(ReportIssueMatch, match_id)
        if record is None:
            raise EntityNotFoundError("ReportIssueMatch", str(match_id))
        if record.status != "PENDING":
            raise MatchAlreadyReviewedError(match_id, record.status)

        now = datetime.datetime.now(datetime.UTC)

        # Optionally link to a different issue
        if link_to_issue_id is not None:
            report = db.get(Report, record.report_id)
            issue = db.get(Issue, link_to_issue_id)
            if report is None:
                raise EntityNotFoundError("Report", str(record.report_id))
            if issue is None:
                raise EntityNotFoundError("Issue", str(link_to_issue_id))
            report.issue_id = issue.id
            record.issue_id = issue.id  # update audit record to reflect actual link
            issue.report_count += 1
            issue.updated_at = now
            from app.services.similarity.service import _running_average
            if report.text_embedding:
                issue.text_embedding = _running_average(
                    issue.text_embedding,
                    report.text_embedding,
                    issue.report_count - 1,
                )
            if report.image_embedding:
                if issue.image_embedding:
                    issue.image_embedding = _running_average(
                        issue.image_embedding,
                        report.image_embedding,
                        issue.report_count - 1,
                    )
                else:
                    issue.image_embedding = list(report.image_embedding)
                    issue.vision_model_version = report.vision_model_version

            # Recompute priority on alternative issue after report linked
            try:
                from app.services.priority.service import apply_priority_to_issue
                apply_priority_to_issue(db, issue)
            except Exception:
                pass  # priority recompute is best-effort

        # Mark other PENDING matches as SUPERSEDED
        self._supersede_other_pending(db, record)

        record.status = "REJECTED"
        record.reviewed_at = now
        record.reviewer_id = reviewer_id
        record.review_notes = notes
        db.flush()

        logger.info(
            "Candidate match REJECTED: match=%s report=%s reviewer=%s",
            match_id, record.report_id, reviewer_id,
        )
        return record

    def get_pending_matches(
        self,
        db: Session,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReportIssueMatch]:
        """Return PENDING candidate matches for human review."""
        stmt = (
            select(ReportIssueMatch)
            .where(ReportIssueMatch.status == "PENDING")
            .order_by(ReportIssueMatch.combined_score.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    def get_match_by_id(
        self,
        db: Session,
        match_id: uuid.UUID,
    ) -> ReportIssueMatch:
        """Retrieve a match record by ID."""
        record = db.get(ReportIssueMatch, match_id)
        if record is None:
            raise EntityNotFoundError("ReportIssueMatch", str(match_id))
        return record

    def _supersede_other_pending(
        self,
        db: Session,
        approved_or_rejected: ReportIssueMatch,
    ) -> None:
        """Mark all other PENDING matches for the same report as SUPERSEDED."""
        stmt = select(ReportIssueMatch).where(
            ReportIssueMatch.report_id == approved_or_rejected.report_id,
            ReportIssueMatch.status == "PENDING",
            ReportIssueMatch.id != approved_or_rejected.id,
        )
        others = list(db.scalars(stmt).all())
        for other in others:
            other.status = "SUPERSEDED"
            other.reviewed_at = datetime.datetime.now(datetime.UTC)


match_review_service = MatchReviewService()
