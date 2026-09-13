from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_pagination
from app.models.enums import PriorityLevel, ReportStatus
from app.schemas.common import PaginationParams
from app.schemas.department import DepartmentDetailRead, DepartmentRead, DepartmentWorkloadStats
from app.schemas.report import ReportListResponse, ReportRead
from app.services.departments.service import department_service

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get(
    "",
    response_model=list[DepartmentRead],
    summary="List municipal departments with operational workload metrics",
)
def list_departments(
    active_only: bool = Query(True, description="Filter for active departments only"),
    db: Session = Depends(get_db),
) -> list[DepartmentRead]:
    """Retrieve all municipal departments, including real-time workload statistics."""
    depts = department_service.list_departments(db, active_only=active_only)
    results: list[DepartmentRead] = []
    for dept in depts:
        stats = department_service.get_workload_stats(db, dept.id)
        d_read = DepartmentRead.model_validate(dept)
        d_read.stats = stats
        results.append(d_read)
    return results


@router.get(
    "/{identifier}",
    response_model=DepartmentDetailRead,
    summary="Get department details by UUID, code, or name",
)
def get_department(
    identifier: str,
    db: Session = Depends(get_db),
) -> DepartmentDetailRead:
    """Retrieve detailed information and full operational stats for a specific department."""
    dept = department_service.get_department(db, identifier)
    stats = department_service.get_workload_stats(db, dept.id)
    d_read = DepartmentDetailRead.model_validate(dept)
    d_read.stats = stats
    return d_read


@router.get(
    "/{identifier}/stats",
    response_model=DepartmentWorkloadStats,
    summary="Get real-time operational workload metrics for a department",
)
def get_department_stats(
    identifier: str,
    db: Session = Depends(get_db),
) -> DepartmentWorkloadStats:
    """Calculate and return live workload counts for the designated department."""
    return department_service.get_workload_stats(db, identifier)


@router.get(
    "/{identifier}/reports",
    response_model=ReportListResponse,
    summary="Get paginated list of reports assigned to a department",
)
def get_department_reports(
    identifier: str,
    status: ReportStatus | None = Query(None, description="Filter by report status"),
    priority: PriorityLevel | None = Query(None, description="Filter by priority level"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """Fetch paginated civic reports assigned to this municipal department."""
    skip = (pagination.page - 1) * pagination.page_size
    items, total = department_service.get_department_reports(
        db,
        identifier=identifier,
        status=status,
        priority=priority,
        skip=skip,
        limit=pagination.page_size,
    )

    sanitized_items: list[ReportRead] = []
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
