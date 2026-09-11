from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_pagination
from app.schemas.ai_job import AIJobEventRead, AIJobRead, ReportAIResult
from app.schemas.common import PaginationParams
from app.schemas.report import (
    ReportCreate,
    ReportListResponse,
    ReportRead,
    ReportTransitionRequest,
)
from app.schemas.verification import VerificationCreate
from app.services.ai.service import ai_service
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
    db: Session = Depends(get_db),
) -> ReportRead:
    """Ingest, validate, and store a new citizen report.

    The report initializes strictly in the `SUBMITTED` state.
    """
    report = report_service.submit_report(db, payload)
    return ReportRead.model_validate(report)


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List civic reports paginated",
)
def list_reports(
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """Retrieve a paginated list of citizen reports sorted by submission time."""
    skip = (pagination.page - 1) * pagination.page_size
    items, total = report_service.list_reports(db, skip=skip, limit=pagination.page_size)

    return ReportListResponse(
        items=[ReportRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


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
