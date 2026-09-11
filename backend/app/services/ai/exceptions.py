from typing import Any

from fastapi import status

from app.core.errors import CivicSenseException


class AIJobNotFoundError(CivicSenseException):
    """Raised when an AI job record does not exist."""

    def __init__(self, identifier: Any) -> None:
        super().__init__(
            message=f"AI processing job '{identifier}' was not found.",
            code="AI_JOB_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class DuplicateActiveJobError(CivicSenseException):
    """Raised when attempting to queue a job while one is already active."""

    def __init__(self, report_id: Any, active_job_id: Any) -> None:
        super().__init__(
            message=(
                f"Report '{report_id}' already has an active AI processing job "
                f"'{active_job_id}'. Multiple concurrent jobs are prohibited."
            ),
            code="DUPLICATE_ACTIVE_JOB",
            status_code=status.HTTP_409_CONFLICT,
            details=[{"report_id": str(report_id), "active_job_id": str(active_job_id)}],
        )


class AIProcessingError(CivicSenseException):
    """Raised when an unexpected error interrupts the AI pipeline."""

    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(
            message=f"AI pipeline execution failed at stage '{stage}': {reason}",
            code="AI_PROCESSING_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{"stage": stage, "reason": reason}],
        )
