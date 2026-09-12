import datetime
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.base import Base
from app.main import app
from app.models.department import DEFAULT_DEPARTMENTS, Department

# In-memory SQLite database isolated per test session
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create fresh database tables for each test function and yield a session."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    now = datetime.datetime.now(datetime.UTC)
    for d in DEFAULT_DEPARTMENTS:
        session.add(
            Department(
                id=d["id"],
                name=d["name"],
                code=d["code"],
                description=d["description"],
                head_name=d["head_name"],
                contact_email=d["contact_email"],
                contact_phone=d["contact_phone"],
                sla_hours_default=d["sla_hours_default"],
                is_active=d["is_active"],
                created_at=now,
                updated_at=now,
            )
        )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_report_payload() -> dict[str, Any]:
    """Sample valid report submission payload adhering to shared contract."""
    return {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address_hint": "Corner of 5th Main and 8th Cross",
        },
        "description": (
            "Deep pothole filled with rainwater near the school entrance. "
            "Hazardous for two-wheelers."
        ),
        "citizen_id": "citizen-anon-001",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "uploads/2026/09/pothole_evidence_01.jpg",
                "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "mime_type": "image/jpeg",
                "file_size_bytes": 204800,
                "metadata_json": {"camera": "mobile_rear", "flash": False},
            }
        ],
    }
