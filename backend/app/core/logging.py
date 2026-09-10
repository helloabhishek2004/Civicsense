import contextvars
import logging
import sys

# Context variable to hold request_id across async coroutines
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class CivicSenseLogFormatter(logging.Formatter):
    """Custom formatter that automatically injects the current request_id and service name."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_ctx.get()
        record.request_id = req_id if req_id else "-"
        record.service = "civicsense-api"
        return super().format(record)


DEFAULT_LOG_FORMAT = (
    "[%(asctime)s] [%(levelname)s] [%(service)s] [req:%(request_id)s] %(name)s: %(message)s"
)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure centralized application logging."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if reloaded
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = CivicSenseLogFormatter(DEFAULT_LOG_FORMAT, datefmt="%Y-%m-%dT%H:%M:%S%z")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for existing_handler in root_logger.handlers:
            existing_handler.setFormatter(
                CivicSenseLogFormatter(DEFAULT_LOG_FORMAT, datefmt="%Y-%m-%dT%H:%M:%S%z")
            )


def get_logger(name: str) -> logging.Logger:
    """Get a named application logger."""
    return logging.getLogger(name)
