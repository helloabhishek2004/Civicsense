from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, request_id_ctx

logger = get_logger(__name__)


class CivicSenseException(Exception):
    """Base exception for all CivicSense domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class EntityNotFoundError(CivicSenseException):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, identifier: Any) -> None:
        super().__init__(
            message=f"{entity_type} with identifier '{identifier}' was not found.",
            code="ENTITY_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidStateTransitionError(CivicSenseException):
    """Raised when an invalid lifecycle state transition is requested."""

    def __init__(self, from_state: str, to_state: str, reason: str | None = None) -> None:
        msg = f"Cannot transition report from '{from_state}' to '{to_state}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(
            message=msg,
            code="INVALID_STATE_TRANSITION",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class MatchAlreadyReviewedError(CivicSenseException):
    """Raised when a match has already been finalized (approved, rejected, or superseded)."""

    def __init__(self, match_id: Any, current_status: str) -> None:
        super().__init__(
            message=(
                f"Match '{match_id}' has already been reviewed "
                f"(current status: {current_status}). "
                "Review actions cannot be repeated on a finalized match."
            ),
            code="MATCH_ALREADY_REVIEWED",
            status_code=status.HTTP_409_CONFLICT,
        )


class DomainValidationError(CivicSenseException):
    """Raised when business validation fails."""

    def __init__(self, message: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class InvalidImagePayloadError(CivicSenseException):
    """Raised when image payload is empty, malformed, or unparseable."""

    def __init__(self, message: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            message=message,
            code="INVALID_IMAGE_PAYLOAD",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class CorruptImageError(CivicSenseException):
    """Raised when image bytes cannot be decoded or are corrupted/truncated."""

    def __init__(self, message: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            message=message,
            code="CORRUPT_IMAGE",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class UnsupportedImageTypeError(CivicSenseException):
    """Raised when an unsupported image format/MIME type is provided."""

    def __init__(self, mime_type: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            message=f"Unsupported image type '{mime_type}'. Allowed types: JPEG, PNG, WEBP.",
            code="UNSUPPORTED_IMAGE_TYPE",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class OversizedImageError(CivicSenseException):
    """Raised when image file byte size exceeds configured limits."""

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            message=(
                f"Image size ({size_bytes / (1024 * 1024):.2f} MB) exceeds maximum allowed limit "
                f"({max_bytes / (1024 * 1024):.2f} MB)."
            ),
            code="IMAGE_TOO_LARGE",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=[{"size_bytes": size_bytes, "max_bytes": max_bytes}],
        )


class ImageDimensionsInvalidError(CivicSenseException):
    """Raised when image width or height falls below minimum or exceeds maximum bounds."""

    def __init__(self, width: int, height: int, min_dim: int, max_dim: int) -> None:
        super().__init__(
            message=(
                f"Image dimensions ({width}x{height}) violate acceptable bounds "
                f"(min {min_dim}x{min_dim}px, max {max_dim}x{max_dim}px)."
            ),
            code="IMAGE_DIMENSIONS_INVALID",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=[{"width": width, "height": height, "min_dim": min_dim, "max_dim": max_dim}],
        )


class ImageDecompressionBombError(CivicSenseException):
    """Raised when image pixel count exceeds decompression bomb threshold."""

    def __init__(self, total_pixels: int, max_pixels: int) -> None:
        super().__init__(
            message=(
                f"Image total pixel count ({total_pixels:,}) exceeds maximum safe threshold "
                f"({max_pixels:,} pixels). Possible decompression bomb."
            ),
            code="IMAGE_DECOMPRESSION_BOMB",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=[{"total_pixels": total_pixels, "max_pixels": max_pixels}],
        )


class TextValidationError(CivicSenseException):
    """Raised when citizen description violates safety, length, or sanitization rules."""

    def __init__(self, message: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            message=message,
            code="TEXT_VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


def create_error_response(
    code: str,
    message: str,
    status_code: int,
    request_id: str | None = None,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Construct a standardized JSON error response."""
    current_req_id = request_id or request_id_ctx.get() or "unknown"
    payload = {
        "error": {
            "code": code,
            "message": message,
            "request_id": current_req_id,
            "details": details or [],
        }
    }
    return JSONResponse(status_code=status_code, content=payload)


async def civicsense_exception_handler(request: Request, exc: CivicSenseException) -> JSONResponse:
    """Handle custom CivicSense domain exceptions."""
    logger.warning("CivicSense exception: code=%s message=%s", exc.code, exc.message)
    return create_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI / Pydantic request validation exceptions."""
    details = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        details.append(
            {
                "field": field,
                "issue": err.get("msg", "Validation error"),
                "type": err.get("type", "value_error"),
            }
        )

    logger.warning("Request validation failed: %d errors", len(details))
    return create_error_response(
        code="VALIDATION_ERROR",
        message="Invalid request payload or query parameters",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected server errors without leaking stack traces."""
    logger.exception("Unhandled server exception: %s", str(exc))
    return create_error_response(
        code="INTERNAL_SERVER_ERROR",
        message=(
            "An unexpected internal server error occurred. "
            "Please refer to request_id for assistance."
        ),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
