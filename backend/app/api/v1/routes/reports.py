import uuid

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_pagination
from app.models.enums import PriorityLevel, ReportStatus
from app.schemas.ai_job import AIJobEventRead, AIJobRead, ReportAIResult
from app.schemas.assignment import (
    AssignmentRead,
    DepartmentAcknowledgeRequest,
    DepartmentAssignRequest,
    DepartmentCompleteRequest,
    DepartmentRejectRequest,
)
from app.schemas.common import PaginationParams
from app.schemas.report import (
    ReportCreate,
    ReportListResponse,
    ReportRead,
    ReportStats,
    ReportTransitionRequest,
)
from app.schemas.verification import VerificationCreate
from app.services.ai.service import ai_service
from app.services.departments.service import department_service
from app.services.reports.service import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a citizen civic report",
)
def create_report(
    payload: ReportCreate,
    response: Response,
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
) -> ReportRead:
    """Ingest, validate, and store a new citizen report.

    The report initializes strictly in the `SUBMITTED` state.
    If the request is an idempotent replay with a recognized client_report_id or
    X-Idempotency-Key, the existing report is returned with HTTP 200 OK.
    """
    if payload.client_report_id is None and x_idempotency_key is not None:
        try:
            payload.client_report_id = uuid.UUID(x_idempotency_key)
        except ValueError:
            pass

    report, is_created = report_service.submit_report(db, payload)
    if not is_created:
        response.status_code = status.HTTP_200_OK
        response.headers["X-Idempotent-Replay"] = "true"

    return ReportRead.model_validate(report)


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List civic reports paginated",
)
def list_reports(
    citizen_id: str | None = Query(
        None,
        max_length=128,
        description="Filter reports by citizen ownership identifier",
    ),
    department: str | None = Query(
        None,
        max_length=64,
        description="Filter reports by assigned department name",
    ),
    status: ReportStatus | None = Query(
        None,
        description="Filter reports by lifecycle status",
    ),
    category: str | None = Query(
        None,
        max_length=64,
        description="Filter reports by civic issue category",
    ),
    priority: PriorityLevel | None = Query(
        None,
        description="Filter reports by priority level",
    ),
    reassignment_required: bool | None = Query(
        None,
        description="Filter reports requiring department reassignment",
    ),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """Retrieve a paginated list of citizen reports sorted by submission time."""
    skip = (pagination.page - 1) * pagination.page_size
    items, total = report_service.list_reports(
        db,
        skip=skip,
        limit=pagination.page_size,
        citizen_id=citizen_id,
        department=department,
        status=status,
        category=category,
        priority=priority,
        reassignment_required=reassignment_required,
    )

    sanitized_items = []
    for item in items:
        r = ReportRead.model_validate(item)
        # Protect citizen contact details in list feeds
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
    "/stats",
    response_model=ReportStats,
    summary="Get aggregated civic report stats",
)
def get_report_stats(
    db: Session = Depends(get_db),
) -> ReportStats:
    """Retrieve operational and workflow metrics across all reports."""
    stats = report_service.get_stats(db)
    return ReportStats.model_validate(stats)


@router.get(
    "/{identifier}",
    response_model=ReportRead,
    summary="Get report by UUID or tracking ID",
)
def get_report(
    identifier: str,
    db: Session = Depends(get_db),
) -> ReportRead:
    """Retrieve detailed report by its internal database UUID or human-readable tracking ID."""
    report = report_service.get_report(db, identifier)
    return ReportRead.model_validate(report)


@router.patch(
    "/{identifier}/transition",
    response_model=ReportRead,
    summary="Transition report lifecycle status",
)
def transition_report_status(
    identifier: str,
    payload: ReportTransitionRequest,
    db: Session = Depends(get_db),
) -> ReportRead:
    """Safely advance report lifecycle status according to canonical state machine rules."""
    report = report_service.transition_status(
        db,
        identifier=identifier,
        new_status=payload.next_status,
        department=payload.department,
        assigned_officer=payload.assigned_officer,
        priority=payload.priority,
        reason=payload.reason,
        notes=payload.notes,
        actor=payload.actor,
    )
    return ReportRead.model_validate(report)


@router.post(
    "/{identifier}/verify",
    response_model=ReportRead,
    summary="Submit human verification verdict on a report",
)
def verify_report(
    identifier: str,
    payload: VerificationCreate,
    db: Session = Depends(get_db),
) -> ReportRead:
    """Submit human review decision (CONFIRMED, CORRECTED, REJECTED, DUPLICATE) on a report."""
    report = report_service.verify_report(db, identifier=identifier, payload=payload)
    return ReportRead.model_validate(report)


@router.post(
    "/{identifier}/ai/process",
    response_model=AIJobRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue and execute AI processing pipeline on report",
)
def process_report_ai(
    identifier: str,
    db: Session = Depends(get_db),
) -> AIJobRead:
    """Execute the 8-stage deterministic prototype AI pipeline for the specified report."""
    job = ai_service.process_report(db, identifier)
    return AIJobRead.model_validate(job)


@router.get(
    "/{identifier}/ai",
    response_model=ReportAIResult,
    summary="Get latest AI assessment and active job status",
)
def get_report_ai(
    identifier: str,
    db: Session = Depends(get_db),
) -> ReportAIResult:
    """Retrieve the latest AI analysis, active job status, and human verification summary."""
    return ai_service.get_report_ai(db, identifier)


@router.get(
    "/{identifier}/ai/events",
    response_model=list[AIJobEventRead],
    summary="Get chronological AI stage audit events for report",
)
def get_report_ai_events(
    identifier: str,
    db: Session = Depends(get_db),
) -> list[AIJobEventRead]:
    """Retrieve all persistent stage-by-stage AI processing events in chronological order."""
    events = ai_service.get_report_events(db, identifier)
    return [AIJobEventRead.model_validate(e) for e in events]


@router.post(
    "/{identifier}/assign",
    response_model=ReportRead,
    summary="Assign or reassign report to a municipal department",
)
def assign_report_department(
    identifier: str,
    payload: DepartmentAssignRequest,
    db: Session = Depends(get_db),
) -> ReportRead:
    """Assign report to a department, advancing to ASSIGNED and logging assignment."""
    report = department_service.assign_report(
        db,
        report_id=identifier,
        department_id=payload.department_id,
        department_name=payload.department_name,
        assigned_by=payload.assigned_by,
        assigned_to_officer=payload.assigned_to_officer,
        notes=payload.notes,
    )
    return ReportRead.model_validate(report)


@router.post(
    "/{identifier}/acknowledge",
    response_model=ReportRead,
    summary="Department acknowledges and accepts assigned job",
)
def acknowledge_report(
    identifier: str,
    payload: DepartmentAcknowledgeRequest,
    db: Session = Depends(get_db),
) -> ReportRead:
    """Department accepts assigned job, advancing status from ASSIGNED to IN_PROGRESS."""
    report = department_service.acknowledge_report(
        db,
        report_id=identifier,
        assigned_to_officer=payload.assigned_to_officer,
        notes=payload.notes,
    )
    return ReportRead.model_validate(report)


@router.post(
    "/{identifier}/complete",
    response_model=ReportRead,
    summary="Department marks work completed",
)
def complete_report(
    identifier: str,
    payload: DepartmentCompleteRequest,
    db: Session = Depends(get_db),
) -> ReportRead:
    """Department officer marks work done with mandatory notes, advancing status to RESOLVED."""
    report = department_service.complete_report(
        db,
        report_id=identifier,
        resolver_notes=payload.resolver_notes,
        resolved_by=payload.resolved_by,
    )
    return ReportRead.model_validate(report)


@router.post(
    "/{identifier}/department-reject",
    response_model=ReportRead,
    summary="Department declines assignment and returns report to triage",
)
def reject_report_assignment(
    identifier: str,
    payload: DepartmentRejectRequest,
    db: Session = Depends(get_db),
) -> ReportRead:
    """Department declines assignment with structured reason.

    Returns report to PRIORITIZED with reassignment_required=True.
    """
    report = department_service.reject_report(
        db,
        report_id=identifier,
        rejection_reason=payload.rejection_reason,
        notes=payload.notes,
        suggested_department=payload.suggested_department,
    )
    return ReportRead.model_validate(report)


@router.get(
    "/{identifier}/assignments",
    response_model=list[AssignmentRead],
    summary="Get complete department assignment history for a report",
)
def get_report_assignments(
    identifier: str,
    db: Session = Depends(get_db),
) -> list[AssignmentRead]:
    """Retrieve all historical assignment attempts and notes for this report."""
    assignments = department_service.get_assignment_history(db, report_id=identifier)
    return [AssignmentRead.model_validate(a) for a in assignments]
