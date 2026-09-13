from fastapi.testclient import TestClient


def test_root_health_check(client: TestClient) -> None:
    """Verify root GET /health returns 200 OK, service metadata, db status, and model readiness."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "civicsense-api"
    assert "version" in data
    assert "database" in data
    assert "models" in data
    assert "pending_candidate_matches" in data
    assert "X-Request-ID" in response.headers


def test_v1_health_check(client: TestClient) -> None:
    """Verify versioned GET /api/v1/health returns 200 OK and diagnostics."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "civicsense-api"
    assert data["database"] == "healthy"
    assert "X-Request-ID" in response.headers


def test_openapi_docs(client: TestClient) -> None:
    """Verify Swagger UI and OpenAPI JSON schemas are served."""
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()
    assert schema["info"]["title"] == "CivicSense API"
    assert "/api/v1/reports" in schema["paths"]


def test_health_zero_pending_matches_does_not_fail(client: TestClient) -> None:
    """Health endpoint succeeds even when pending_candidate_matches == 0."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # Zero pending matches is a valid operational state, not an error
    assert isinstance(data["pending_candidate_matches"], int)
    assert data["pending_candidate_matches"] >= 0
    assert data["status"] in ("ok", "degraded")


def test_health_timestamp_format(client: TestClient) -> None:
    """Health timestamp is ISO 8601 UTC with Z suffix."""
    response = client.get("/health")
    assert response.status_code == 200
    ts = response.json().get("timestamp", "")
    assert ts.endswith("Z"), f"Expected UTC 'Z' suffix in timestamp: {ts!r}"
    assert "T" in ts, f"Expected ISO 8601 datetime separator: {ts!r}"


def test_health_no_credentials_or_pii_in_response(client: TestClient) -> None:
    """Health response must not expose credentials, stack traces, or internal paths."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.text
    for forbidden in ("password", "secret", "token", "Traceback"):
        assert forbidden not in body, (
            f"Health response must not expose '{forbidden}' in output"
        )


def test_health_model_degraded_field_present(client: TestClient) -> None:
    """Health models section includes degraded_mode field (True or False)."""
    response = client.get("/health")
    assert response.status_code == 200
    models = response.json().get("models", {})
    assert "degraded_mode" in models
    assert isinstance(models["degraded_mode"], bool)
