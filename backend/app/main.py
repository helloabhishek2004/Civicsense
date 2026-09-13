import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.api.v1.api import api_v1_router
from app.api.v1.routes.health import router as health_router
from app.core.config import get_settings
from app.core.errors import (
    CivicSenseException,
    civicsense_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import get_logger, request_id_ctx, setup_logging

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger("civicsense.api")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to inject/propagate X-Request-ID and log request completion metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract or generate unique request ID
        incoming_req_id = request.headers.get("X-Request-ID")
        req_id = incoming_req_id if incoming_req_id else str(uuid.uuid4())

        token = request_id_ctx.set(req_id)
        request.state.request_id = req_id

        start_time = time.perf_counter()
        logger.info("Incoming request: %s %s", request.method, request.url.path)

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            response.headers["X-Request-ID"] = req_id
            logger.info(
                "Completed %s %s -> status=%d (%.2fms)",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            return response
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Request failed: %s %s (%.2fms)",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        finally:
            request_id_ctx.reset(token)


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="CivicSense API",
        description=(
            "CivicSense — From Citizen Reports to Civic Intelligence.\n"
            "Hybrid edge-cloud civic issue reporting, validation, and analytics platform."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Middleware
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    app.add_exception_handler(CivicSenseException, civicsense_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Root Health check
    app.include_router(health_router, tags=["Health"])

    # Static uploads directory for evidence media
    uploads_path = Path(settings.UPLOADS_DIR)
    uploads_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

    # Versioned API
    app.include_router(api_v1_router, prefix="/api/v1")

    # Validate MiniLM model at startup
    @app.on_event("startup")
    def _validate_similarity_model() -> None:
        from app.services.similarity.service import validate_model_availability

        report = validate_model_availability()
        if report["degraded_mode"]:
            logger.warning(
                "Similarity engine running in DEGRADED mode: %s",
                report.get("load_error", "model not found"),
            )
        else:
            logger.info(
                "Similarity engine ready: model=%s dim=%d version=%s",
                report["model_dir"],
                report["embedding_dim"],
                settings.SIMILARITY_EMBEDDING_MODEL_VERSION,
            )

    return app


app = create_application()
