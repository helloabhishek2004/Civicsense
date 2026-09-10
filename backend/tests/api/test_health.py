from fastapi.testclient import TestClient


def test_root_health_check(client: TestClient) -> None:
    """Verify root GET /health returns 200 OK and service metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "civicsense-api"
    assert "version" in data
    assert "X-Request-ID" in response.headers


def test_v1_health_check(client: TestClient) -> None:
    """Verify versioned GET /api/v1/health returns 200 OK."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "civicsense-api"
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
