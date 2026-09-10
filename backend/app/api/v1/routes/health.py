from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=dict[str, Any])
def health_check() -> dict[str, Any]:
    """Health and liveness probe for the CivicSense API."""
    return {
        "status": "ok",
        "service": "civicsense-api",
        "version": "0.1.0",
    }
