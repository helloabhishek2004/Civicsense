import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models.report_issue_match import ReportIssueMatch
from app.services.similarity.service import validate_model_availability

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=dict[str, Any])
def health_check(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Operational health, model readiness, and diagnostic probe for the CivicSense API."""
    db_status = "unhealthy"
    pending_matches_count = 0

    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
        total_stmt = select(func.count()).select_from(ReportIssueMatch).where(
            ReportIssueMatch.status == "PENDING"
        )
        pending_matches_count = db.scalar(total_stmt) or 0
    except Exception:
        db_status = "unreachable"

    model_report = validate_model_availability()
    overall_status = "ok" if db_status == "healthy" else "degraded"

    return {
        "status": overall_status,
        "service": "civicsense-api",
        "version": "0.1.0",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
        "database": db_status,
        "models": {
            "minilm": model_report.get("status", "UNKNOWN"),
            "degraded_mode": model_report.get("degraded_mode", False),
        },
        "pending_candidate_matches": pending_matches_count,
    }
