from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_pagination
from app.schemas.common import PaginationParams
from app.schemas.report import ReportCreate, ReportListResponse, ReportRead
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
