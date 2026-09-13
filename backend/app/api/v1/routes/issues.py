"""API endpoints for Issue listing with priority ranking and breakdown."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_pagination
from app.core.logging import get_logger
from app.models.issue import Issue
from app.schemas.common import PaginationParams
from app.schemas.issue import IssueListResponse, IssueRead, PriorityBreakdownRead
from app.schemas.report import ReportListResponse, ReportRead
from app.services.priority.service import (
    apply_priority_to_issue,
    recompute_all_priorities,
)
from app.services.reports.service import report_service

logger = get_logger(__name__)

router = APIRouter(prefix="/issues", tags=["Issues"])

# ---------------------------------------------------------------------------
# Authorization: admin header for batch recompute
# ---------------------------------------------------------------------------

ADMIN_HEADER = "X-Admin-ID"


def _require_admin(
    x_admin_id: str | None = Header(None, alias=ADMIN_HEADER),
) -> str:
    if not x_admin_id or not x_admin_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "ADMIN_AUTH_REQUIRED",
                "message": "X-Admin-ID header is required for admin actions.",
            },
        )
    return x_admin_id.strip()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=IssueListResponse,
    summary="List issues sorted by priority",
)
def list_issues(
    pagination: PaginationParams = Depends(get_pagination),
    sort: str = Query(
        "priority",
        description="Sort field: 'priority', 'created', 'updated', 'reports'",
    ),
    order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    category: str | None = Query(None, max_length=64, description="Filter by category"),
    issue_status: str | None = Query(
        None, alias="status", max_length=32, description="Filter by status"
    ),
    db: Session = Depends(get_db),
) -> IssueListResponse:
    """Return issues ranked by priority score (default) or other sort fields."""
    stmt = select(Issue)

    if category:
        stmt = stmt.where(Issue.category == category)
    if issue_status:
        stmt = stmt.where(Issue.status == issue_status)

    # Sorting
    sort_map: dict[str, Any] = {
        "priority": Issue.priority_score.desc().nullslast(),
        "created": Issue.created_at.desc() if order == "desc" else Issue.created_at.asc(),
        "updated": Issue.updated_at.desc() if order == "desc" else Issue.updated_at.asc(),
        "reports": Issue.report_count.desc() if order == "desc" else Issue.report_count.asc(),
    }
    stmt = stmt.order_by(sort_map.get(sort, sort_map["priority"]))

    # Total count
    count_stmt = select(func.count()).select_from(Issue)
    if category:
        count_stmt = count_stmt.where(Issue.category == category)
    if issue_status:
        count_stmt = count_stmt.where(Issue.status == issue_status)
    total = db.scalar(count_stmt) or 0

    # Paginate
    offset = (pagination.page - 1) * pagination.page_size
    stmt = stmt.offset(offset).limit(pagination.page_size)
    issues = list(db.scalars(stmt).all())

    return IssueListResponse(
        items=[IssueRead.model_validate(i) for i in issues],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/{issue_id}/reports",
    response_model=ReportListResponse,
    summary="Get reports linked to an issue",
)
def get_issue_reports(
    issue_id: uuid.UUID,
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """Retrieve reports linked to a specific aggregated issue."""
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ISSUE_NOT_FOUND", "message": f"Issue {issue_id} not found"},
        )
    skip = (pagination.page - 1) * pagination.page_size
    items, total = report_service.list_reports(
        db,
        skip=skip,
        limit=pagination.page_size,
        issue_id=issue_id,
    )
    sanitized_items = []
    for item in items:
        r = ReportRead.model_validate(item)
        r.citizen_phone = None
        r.citizen_email = None
        r.citizen_postal_code = None
        sanitized_items.append(r)

    return ReportListResponse(
        items=sanitized_items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/{issue_id}",
    response_model=IssueRead,
    summary="Get a single issue by ID",
)
def get_issue(
    issue_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> IssueRead:
    """Return a single issue with its priority fields."""
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ISSUE_NOT_FOUND", "message": f"Issue {issue_id} not found"},
        )
    return IssueRead.model_validate(issue)


@router.get(
    "/{issue_id}/priority",
    response_model=PriorityBreakdownRead,
    summary="Get priority breakdown for an issue",
)
def get_issue_priority(
    issue_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PriorityBreakdownRead:
    """Return the full priority breakdown including component scores."""
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ISSUE_NOT_FOUND", "message": f"Issue {issue_id} not found"},
        )

    # Recompute on demand if stale or missing
    if issue.priority_computed_at is None:
        apply_priority_to_issue(db, issue)
        db.refresh(issue)

    return PriorityBreakdownRead(
        issue_id=issue.id,
        priority_score=issue.priority_score,
        priority_level=issue.priority_level,
        priority_computed_at=issue.priority_computed_at,
        breakdown=issue.priority_breakdown,
    )


@router.post(
    "/recompute-priority",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch recompute priority for all issues (admin only)",
)
def batch_recompute_priority(
    status_filter: str | None = Query(
        None, description="Only recompute issues with this status (e.g. 'OPEN')"
    ),
    batch_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _admin: str = Depends(_require_admin),
) -> dict[str, Any]:
    """Recompute priority for all matching issues.

    Protected by X-Admin-ID header. Processes in batches to avoid memory issues.
    """
    summary = recompute_all_priorities(
        db,
        batch_size=batch_size,
        status_filter=status_filter,
    )
    return summary
