import datetime

from pydantic import BaseModel, Field


def ensure_utc(dt: datetime.datetime | None) -> datetime.datetime | None:
    """Ensure datetime is explicitly timezone-aware in UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.UTC)
    return dt.astimezone(datetime.UTC)


class LocationSchema(BaseModel):
    """Geographic coordinate representation."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    address_hint: str | None = Field(
        None, max_length=255, description="Optional street or landmark hint"
    )


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    page: int = Field(1, ge=1, description="1-indexed page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
