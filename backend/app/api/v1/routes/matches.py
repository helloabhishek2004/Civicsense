"""API endpoints for reviewing, approving, or rejecting dedup candidate matches.

Authorization: Only municipal/admin reviewers (X-Reviewer-ID header) may perform
review actions. This is a lightweight header-based check for prototype; production
should use JWT/role-based auth.
"""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_pagination
from app.core.errors import EntityNotFoundError, MatchAlreadyReviewedError
from app.core.logging import get_logger
from app.schemas.common import PaginationParams
from app.schemas.match_review import (
    ApproveRequest,
    MatchListResponse,
    MatchRead,
    RejectRequest,
    ReviewActionResponse,
    UnifiedReviewRequest,
)
from app.services.similarity.review import MatchReviewService

logger = get_logger(__name__)

router = APIRouter(prefix="/matches", tags=["Match Review"])

review_service = MatchReviewService()

# ---------------------------------------------------------------------------
# Authorization: lightweight header-based reviewer identity
# ---------------------------------------------------------------------------

# Prototype authorization: any non-empty X-Reviewer-ID header is accepted.
# Production should enforce JWT claims, role-based access, or session-based auth.
REVIEWER_HEADER = "X-Reviewer-ID"


def _require_reviewer(
    x_reviewer_id: str | None = Header(None, alias=REVIEWER_HEADER),
) -> str:
    """Extract and validate the reviewer identity from request header.

    Raises 401 if the header is missing or empty.
    """
    if not x_reviewer_id or not x_reviewer_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "REVIEWER_AUTH_REQUIRED",
                "message": "X-Reviewer-ID header is required for match review actions.",
            },
        )
    return x_reviewer_id.strip()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/pending",
    response_model=MatchListResponse,
    summary="List pending candidate matches for human review",
)
def list_pending_matches(
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
    _reviewer: str = Depends(_require_reviewer),
) -> MatchListResponse:
    """Return PENDING candidate matches ordered by combined_score descending.

    Requires a valid X-Reviewer-ID header.
    """
    matches = review_service.get_pending_matches(
        db,
        limit=pagination.page_size,
        offset=(pagination.page - 1) * pagination.page_size,
    )

    # Get total count of pending matches
    from sqlalchemy import func, select

    from app.models.report_issue_match import ReportIssueMatch

    total_stmt = select(func.count()).select_from(ReportIssueMatch).where(
        ReportIssueMatch.status == "PENDING"
    )
    total = db.scalar(total_stmt) or 0

    return MatchListResponse(
        items=[MatchRead.model_validate(m) for m in matches],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "",
    response_model=MatchListResponse,
    summary="List matches with optional status filter for audit querying",
)
def list_matches(
    match_status: str | None = Query(
        None, alias="status", max_length=32,
        description="Filter by match status (e.g. PENDING, APPROVED, REJECTED, SUPERSEDED)",
    ),
    report_id: uuid.UUID | None = Query(None, description="Filter by report ID"),
    issue_id: uuid.UUID | None = Query(None, description="Filter by issue ID"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
    _reviewer: str = Depends(_require_reviewer),
) -> MatchListResponse:
    """Return paginated similarity matches for operational review and audit logging.

    Requires a valid X-Reviewer-ID header.
    """
    from sqlalchemy import func, select

    from app.models.report_issue_match import ReportIssueMatch

    stmt = select(ReportIssueMatch)
    count_stmt = select(func.count()).select_from(ReportIssueMatch)

    if match_status:
        stmt = stmt.where(ReportIssueMatch.status == match_status.strip().upper())
        count_stmt = count_stmt.where(ReportIssueMatch.status == match_status.strip().upper())
    if report_id:
        stmt = stmt.where(ReportIssueMatch.report_id == report_id)
        count_stmt = count_stmt.where(ReportIssueMatch.report_id == report_id)
    if issue_id:
        stmt = stmt.where(ReportIssueMatch.issue_id == issue_id)
        count_stmt = count_stmt.where(ReportIssueMatch.issue_id == issue_id)

    stmt = stmt.order_by(ReportIssueMatch.created_at.desc())
    total = db.scalar(count_stmt) or 0

    offset = (pagination.page - 1) * pagination.page_size
    stmt = stmt.offset(offset).limit(pagination.page_size)
    matches = list(db.scalars(stmt).all())

    return MatchListResponse(
        items=[MatchRead.model_validate(m) for m in matches],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/{match_id}",
    response_model=MatchRead,
    summary="Get detailed match record by ID for audit trail",
)
def get_match(
    match_id: uuid.UUID,
    db: Session = Depends(get_db),
    _reviewer: str = Depends(_require_reviewer),
) -> MatchRead:
    """Retrieve an individual match decision record by ID."""
    try:
        record = review_service.get_match_by_id(db, match_id)
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return MatchRead.model_validate(record)


@router.post(
    "/{match_id}/approve",
    response_model=ReviewActionResponse,
    summary="Approve a candidate match",
)
def approve_match(
    match_id: uuid.UUID,
    payload: ApproveRequest,
    db: Session = Depends(get_db),
    _reviewer: str = Depends(_require_reviewer),
) -> ReviewActionResponse:
    """Approve a PENDING candidate: link the report to the candidate issue.

    The header X-Reviewer-ID must match the payload reviewer_id for audit consistency.
    """
    if _reviewer != payload.reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "REVIEWER_MISMATCH",
                "message": "X-Reviewer-ID header must match reviewer_id in request body.",
            },
        )

    try:
        record = review_service.approve_candidate(
            db,
            match_id,
            reviewer_id=payload.reviewer_id,
            notes=payload.notes,
        )
    except MatchAlreadyReviewedError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_MATCH", "message": str(exc)},
        ) from exc

    db.commit()
    db.refresh(record)
    return ReviewActionResponse(
        match_id=record.id,
        status=record.status,
        report_id=record.report_id,
        issue_id=record.issue_id,
        reviewer_id=record.reviewer_id or payload.reviewer_id,
        reviewed_at=record.reviewed_at,
    )


@router.post(
    "/{match_id}/reject",
    response_model=ReviewActionResponse,
    summary="Reject a candidate match",
)
def reject_match(
    match_id: uuid.UUID,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    _reviewer: str = Depends(_require_reviewer),
) -> ReviewActionResponse:
    """Reject a PENDING candidate: leave the report unlinked (or link to alternate issue).

    The header X-Reviewer-ID must match the payload reviewer_id for audit consistency.
    """
    if _reviewer != payload.reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "REVIEWER_MISMATCH",
                "message": "X-Reviewer-ID header must match reviewer_id in request body.",
            },
        )

    try:
        record = review_service.reject_candidate(
            db,
            match_id,
            reviewer_id=payload.reviewer_id,
            notes=payload.notes,
            link_to_issue_id=payload.link_to_issue_id,
        )
    except MatchAlreadyReviewedError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    db.commit()
    db.refresh(record)
    return ReviewActionResponse(
        match_id=record.id,
        status=record.status,
        report_id=record.report_id,
        issue_id=record.issue_id,
        reviewer_id=record.reviewer_id or payload.reviewer_id,
        reviewed_at=record.reviewed_at,
    )


@router.post(
    "/{match_id}/review",
    response_model=ReviewActionResponse,
    summary="Review a candidate match (unified approve or reject)",
)
def review_match(
    match_id: uuid.UUID,
    payload: UnifiedReviewRequest,
    db: Session = Depends(get_db),
    _reviewer: str = Depends(_require_reviewer),
) -> ReviewActionResponse:
    """Perform a review action (APPROVE or REJECT) on a candidate match."""
    action_upper = payload.action.strip().upper()
    if action_upper == "APPROVE":
        approve_req = ApproveRequest(
            reviewer_id=payload.reviewer_id,
            notes=payload.notes,
        )
        return approve_match(match_id, approve_req, db, _reviewer)
    elif action_upper == "REJECT":
        reject_req = RejectRequest(
            reviewer_id=payload.reviewer_id,
            notes=payload.notes,
            link_to_issue_id=payload.link_to_issue_id,
        )
        return reject_match(match_id, reject_req, db, _reviewer)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_ACTION",
                "message": (
                    f"Unknown review action '{payload.action}'. "
                    "Expected 'APPROVE' or 'REJECT'."
                ),
            },
        )

