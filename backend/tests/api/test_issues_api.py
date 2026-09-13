import uuid
from typing import Any

from fastapi.testclient import TestClient


def test_get_issue_reports_success(client: TestClient, sample_report_payload: dict[str, Any]) -> None:
    """Test retrieving reports linked to an issue."""
    # Create report which automatically creates/links an issue
    res = client.post("/api/v1/reports", json=sample_report_payload)
    assert res.status_code == 201
    report_data = res.json()
    issue_id = report_data.get("issue_id")
    assert issue_id is not None

    # Fetch reports for this issue
    resp = client.get(f"/api/v1/issues/{issue_id}/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(r["id"] == report_data["id"] for r in data["items"])
    # Verify privacy sanitization
    for r in data["items"]:
        assert r["citizen_phone"] is None
        assert r["citizen_email"] is None
        assert r["citizen_postal_code"] is None


def test_get_issue_reports_not_found(client: TestClient) -> None:
    """Test 404 for non-existent issue ID."""
    random_id = uuid.uuid4()
    resp = client.get(f"/api/v1/issues/{random_id}/reports")
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == "ISSUE_NOT_FOUND"


def test_list_reports_filter_by_issue_id(client: TestClient, sample_report_payload: dict[str, Any]) -> None:
    """Test filtering /api/v1/reports by issue_id."""
    res = client.post("/api/v1/reports", json=sample_report_payload)
    assert res.status_code == 201
    report_data = res.json()
    issue_id = report_data.get("issue_id")
    assert issue_id is not None

    # Query reports with issue_id filter
    resp = client.get(f"/api/v1/reports?issue_id={issue_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert all(r["issue_id"] == issue_id for r in data["items"])

    # Query with non-existent issue_id
    empty_resp = client.get(f"/api/v1/reports?issue_id={uuid.uuid4()}")
    assert empty_resp.status_code == 200
    assert empty_resp.json()["total"] == 0
