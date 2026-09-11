from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_pagination
from app.models.enums import AIJobStatus, AIProcessingStage
from app.schemas.ai_job import AIHealthResponse, AIJobListResponse, AIJobRead
from app.schemas.ai_metrics import AIMetricsResponse
from app.schemas.common import PaginationParams
from app.services.ai.service import ai_service

router = APIRouter(prefix="/ai", tags=["AI Operations"])


@router.get(
    "/jobs",
    response_model=AIJobListResponse,
    summary="List all AI processing jobs",
)
def list_ai_jobs(
    status: AIJobStatus | None = Query(None, description="Filter by job status"),
    stage: AIProcessingStage | None = Query(None, description="Filter by current pipeline stage"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
) -> AIJobListResponse:
    """Retrieve paginated list of AI processing jobs across all reports."""
    skip = (pagination.page - 1) * pagination.page_size
    items, total = ai_service.list_jobs(
        db, status=status, stage=stage, skip=skip, limit=pagination.page_size
    )
    return AIJobListResponse(
        items=[AIJobRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/metrics",
    response_model=AIMetricsResponse,
    summary="Get real database-derived AI metrics",
)
def get_ai_metrics(db: Session = Depends(get_db)) -> AIMetricsResponse:
    """Compute aggregate AI metrics directly from database records without hardcoded values."""
    return ai_service.get_metrics(db)


@router.get(
    "/health",
    response_model=AIHealthResponse,
    summary="Get AI worker health and truthful capability disclosure",
)
def get_ai_health(db: Session = Depends(get_db)) -> AIHealthResponse:
    """Return live status of AI processor, execution mode, and capability disclosure."""
    return ai_service.get_health(db)
