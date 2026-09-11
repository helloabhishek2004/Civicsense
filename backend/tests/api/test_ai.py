from typing import Any

from fastapi.testclient import TestClient


def test_ai_health_endpoint(client: TestClient) -> None:
    """Verify truthful health and capability disclosure endpoint."""
    response = client.get("/api/v1/ai/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "available"
    assert data["processor_mode"] == "deterministic_demo"
    assert data["production_model_available"] is False
    assert data["background_worker_available"] is False
    assert "INTAKE_VALIDATION" in data["supported_stages"]
    assert "COMPLETED" in data["supported_stages"]


def test_ai_metrics_initial_state(client: TestClient) -> None:
    """Verify real metrics return clean state or insufficient data instead of fake numbers."""
    response = client.get("/api/v1/ai/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_jobs"]["value"] == 0
    assert data["total_jobs"]["display_state"] == "AVAILABLE"
    # When no completed jobs exist, latency is INSUFFICIENT_DATA
    assert data["avg_processing_latency_ms"]["display_state"] == "INSUFFICIENT_DATA"


def test_process_report_ai_complete_pipeline(
    client: TestClient, sample_report_payload: dict[str, Any]
) -> None:
    """Test full 8-stage processing on a submitted report."""
    # 1. Create a report
    create_res = client.post("/api/v1/reports", json=sample_report_payload)
    assert create_res.status_code == 201
    report_data = create_res.json()
    report_id = report_data["id"]
    assert report_data["status"] == "SUBMITTED"

    # 2. Trigger AI processing
    process_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert process_res.status_code == 202
    job_data = process_res.json()
    assert job_data["status"] == "COMPLETED"
    assert job_data["processor_name"] == "Deterministic Demo Processor"
    assert len(job_data["events"]) >= 6

    # 3. Check report AI summary
    ai_summary_res = client.get(f"/api/v1/reports/{report_id}/ai")
    assert ai_summary_res.status_code == 200
    ai_summary = ai_summary_res.json()
    assert ai_summary["latest_job"]["id"] == job_data["id"]
    assert ai_summary["ai_analysis"] is not None
    assert ai_summary["ai_analysis"]["predicted_category"] == "Pothole"
    assert ai_summary["ai_analysis"]["confidence"] >= 0.70

    # 4. Check chronological events
    events_res = client.get(f"/api/v1/reports/{report_id}/ai/events")
    assert events_res.status_code == 200
    events = events_res.json()
    stages = [e["stage"] for e in events]
    assert "INTAKE_VALIDATION" in stages
    assert "PREPROCESSING" in stages
    assert "VISION_ANALYSIS" in stages
    assert "TEXT_ANALYSIS" in stages
    assert "FUSION" in stages
    assert "DECISION" in stages

    # 5. Check jobs endpoint
    jobs_res = client.get("/api/v1/ai/jobs")
    assert jobs_res.status_code == 200
    jobs_list = jobs_res.json()
    assert jobs_list["total"] >= 1
    assert any(j["id"] == job_data["id"] for j in jobs_list["items"])

    # 6. Check metrics updated with real DB count
    metrics_res = client.get("/api/v1/ai/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["total_jobs"]["value"] >= 1
    assert metrics["completed_jobs"]["value"] >= 1


def test_ai_low_confidence_routes_to_verification_required(client: TestClient) -> None:
    """Test that vague/unclassified description triggers human review requirement."""
    # Create report with ambiguous description
    vague_payload = {
        "location": {"latitude": 12.9716, "longitude": 77.5946},
        "description": "Something strange is happening on the street corner. Please check.",
        "evidence": [],
    }
    create_res = client.post("/api/v1/reports", json=vague_payload)
    assert create_res.status_code == 201
    report_id = create_res.json()["id"]

    # Process AI
    process_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert process_res.status_code == 202
    job_data = process_res.json()

    # Must be marked review_required and current_stage HUMAN_REVIEW
    assert job_data["review_required"] is True
    assert job_data["current_stage"] == "HUMAN_REVIEW"

    # Report status must advance to VERIFICATION_REQUIRED
    report_res = client.get(f"/api/v1/reports/{report_id}")
    assert report_res.status_code == 200
    assert report_res.json()["status"] == "VERIFICATION_REQUIRED"
