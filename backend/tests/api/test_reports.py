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


def test_transition_report_status_valid_and_invalid(
    client: TestClient, sample_report_payload: dict[str, Any]
) -> None:
    """Verify state transitions via PATCH /api/v1/reports/{id}/transition."""
    create_resp = client.post("/api/v1/reports", json=sample_report_payload)
    assert create_resp.status_code == 201
    report = create_resp.json()
    report_id = report["id"]
    assert report["status"] == "SUBMITTED"

    # Valid transition: SUBMITTED -> AI_PROCESSING
    patch_resp = client.patch(
        f"/api/v1/reports/{report_id}/transition",
        json={"next_status": "AI_PROCESSING", "actor": "Test Officer"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "AI_PROCESSING"

    # Invalid transition: AI_PROCESSING -> RESOLVED (Illegal skip)
    invalid_patch = client.patch(
        f"/api/v1/reports/{report_id}/transition",
        json={"next_status": "RESOLVED"},
    )
    assert invalid_patch.status_code == 400
    assert invalid_patch.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_verify_report_endpoint(client: TestClient, sample_report_payload: dict[str, Any]) -> None:
    """Verify human review verdict via POST /api/v1/reports/{id}/verify."""
    create_resp = client.post("/api/v1/reports", json=sample_report_payload)
    assert create_resp.status_code == 201
    report_id = create_resp.json()["id"]

    # Transition to AI_PROCESSING -> AI_PROCESSED -> VERIFICATION_REQUIRED
    client.patch(f"/api/v1/reports/{report_id}/transition", json={"next_status": "AI_PROCESSING"})
    client.patch(
        f"/api/v1/reports/{report_id}/transition", json={"next_status": "VERIFICATION_REQUIRED"}
    )

    # Verify report with CONFIRMED decision
    verify_resp = client.post(
        f"/api/v1/reports/{report_id}/verify",
        json={
            "decision": "CONFIRMED",
            "reviewer_id": "Officer Sharma",
            "verified_category": "Pothole",
            "verified_severity": "HIGH",
            "notes": "Verified severe pothole requiring priority resurfacing.",
        },
    )
    assert verify_resp.status_code == 200
    updated = verify_resp.json()
    assert updated["status"] == "VERIFIED"
    assert len(updated["verifications"]) == 1
    assert updated["verifications"][0]["decision"] == "CONFIRMED"
    assert updated["verifications"][0]["reviewer_id"] == "Officer Sharma"
    assert updated["verifications"][0]["verified_severity"] == "HIGH"


def test_create_report_idempotent_replay(
    client: TestClient, sample_report_payload: dict[str, Any]
) -> None:
    """Submitting the same client_report_id twice must replay original report with HTTP 200."""
    import uuid

    client_id = str(uuid.uuid4())
    payload = sample_report_payload.copy()
    payload["client_report_id"] = client_id

    # First submission
    first_resp = client.post("/api/v1/reports", json=payload)
    assert first_resp.status_code == 201
    first_data = first_resp.json()

    # Second submission with same client_report_id
    second_resp = client.post("/api/v1/reports", json=payload)
    assert second_resp.status_code == 200
    assert second_resp.headers.get("X-Idempotent-Replay") == "true"
    second_data = second_resp.json()

    # Both responses must refer to the exact same report
    assert first_data["id"] == second_data["id"]
    assert first_data["tracking_id"] == second_data["tracking_id"]


def test_get_report_stats(client: TestClient, sample_report_payload: dict[str, Any]) -> None:
    """GET /api/v1/reports/stats must return 200 with aggregated operational metrics."""
    client.post("/api/v1/reports", json=sample_report_payload)
    resp = client.get("/api/v1/reports/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "totalReports" in data
    assert "pendingReview" in data
    assert "inProgress" in data
    assert "resolvedToday" in data
    assert "criticalIssues" in data
    assert data["totalReports"] >= 1
