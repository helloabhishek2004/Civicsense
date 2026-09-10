from fastapi import Query

from app.db.session import get_db
from app.schemas.common import PaginationParams


def get_pagination(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    """Dependency extracting pagination query parameters."""
    return PaginationParams(page=page, page_size=page_size)


__all__ = ["get_db", "get_pagination"]
