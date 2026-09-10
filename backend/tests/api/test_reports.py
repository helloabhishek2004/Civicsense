from typing import Any

from fastapi.testclient import TestClient


def test_create_report_success(client: TestClient, sample_report_payload: dict[str, Any]) -> None:
    """Test successful report submission through POST /api/v1/reports."""
    response = client.post("/api/v1/reports", json=sample_report_payload)
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["tracking_id"].startswith("REP-")
    assert data["status"] == "SUBMITTED"
    assert data["description"] == sample_report_payload["description"]
    assert data["latitude"] == sample_report_payload["location"]["latitude"]
    assert data["longitude"] == sample_report_payload["location"]["longitude"]
    assert len(data["evidences"]) == 1
    assert data["evidences"][0]["evidence_type"] == "IMAGE"
    assert "X-Request-ID" in response.headers


def test_get_report_by_id_and_tracking_id(
    client: TestClient, sample_report_payload: dict[str, Any]
) -> None:
    """Test retrieving report by internal UUID and human tracking ID."""
    create_resp = client.post("/api/v1/reports", json=sample_report_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    report_id = created["id"]
    tracking_id = created["tracking_id"]

    # Retrieve by UUID
    get_uuid_resp = client.get(f"/api/v1/reports/{report_id}")
    assert get_uuid_resp.status_code == 200
    assert get_uuid_resp.json()["id"] == report_id

    # Retrieve by Tracking ID
    get_tracking_resp = client.get(f"/api/v1/reports/{tracking_id}")
    assert get_tracking_resp.status_code == 200
    assert get_tracking_resp.json()["tracking_id"] == tracking_id


def test_list_reports_pagination(client: TestClient, sample_report_payload: dict[str, Any]) -> None:
    """Test paginated retrieval of reports."""
    for i in range(3):
        payload = sample_report_payload.copy()
        payload["description"] = f"Report test #{i}"
        client.post("/api/v1/reports", json=payload)

    resp = client.get("/api/v1/reports?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


def test_get_nonexistent_report_returns_standard_error(client: TestClient) -> None:
    """Verify 404 returns unified error JSON schema."""
    resp = client.get("/api/v1/reports/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "ENTITY_NOT_FOUND"
    assert "request_id" in body["error"]


def test_create_report_validation_failure(client: TestClient) -> None:
    """Verify invalid payloads return 422 with structured validation errors."""
    invalid_payload = {
        "location": {
            "latitude": 150.0,  # Invalid latitude (> 90)
            "longitude": 77.0,
        },
        "description": "ab",  # Too short (< 3 chars)
    }
    resp = client.post("/api/v1/reports", json=invalid_payload)
    assert resp.status_code == 422
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert len(body["error"]["details"]) >= 2
