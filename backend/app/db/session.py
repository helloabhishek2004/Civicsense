from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

connect_args: dict[str, Any] = {}
engine_kwargs: dict[str, Any] = {}
database_url = settings.DATABASE_URL

if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    engine_kwargs["poolclass"] = NullPool
    if database_url.startswith("sqlite:///") and not database_url.startswith("sqlite:////"):
        rel_path = database_url[len("sqlite:///"):]
        if rel_path.startswith("./") or rel_path.startswith(".\\"):
            rel_path = rel_path[2:]
        from app.core.config import _BACKEND_DIR
        candidate = _BACKEND_DIR / rel_path
        if candidate.exists():
            database_url = f"sqlite:///{candidate.resolve().as_posix()}"
else:
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(
    database_url,
    connect_args=connect_args,
    **engine_kwargs,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining transactional database sessions in FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
