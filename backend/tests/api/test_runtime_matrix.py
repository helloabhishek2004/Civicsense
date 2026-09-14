from fastapi.testclient import TestClient


def test_case_a_high_confidence_agreement(client: TestClient) -> None:
    """Case A: High-confidence image + text yields AI_PROCESSED and review_required=False."""
    create_payload = {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address_hint": "Main Road, Cross 5",
        },
        "description": "Large deep pothole in asphalt near intersection causing tire damage.",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "uploads/pothole_asphalt_hazard.jpg",
                "file_hash": "a" * 64,
                "mime_type": "image/jpeg",
                "file_size_bytes": 2048500,
                "metadata_json": {"prototype_category": "Pothole"},
            }
        ],
    }
    create_res = client.post("/api/v1/reports", json=create_payload)
    assert create_res.status_code == 201
    report_data = create_res.json()
    report_id = report_data["id"]
    assert report_data["status"] != "SUBMITTED"  # AI runs automatically

    # Manual trigger is idempotent after auto-processing
    proc_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert proc_res.status_code == 202
    job_data = proc_res.json()

    assert job_data["status"] == "COMPLETED"
    assert job_data["review_required"] is False
    assert job_data["current_stage"] == "COMPLETED"
    assert len(job_data["events"]) == 7

    get_res = client.get(f"/api/v1/reports/{report_id}")
    assert get_res.status_code == 200
    updated_report = get_res.json()
    assert updated_report["status"] == "AI_PROCESSED"
    assert len(updated_report["ai_analyses"]) >= 1

    latest_ai = updated_report["ai_analyses"][0]
    assert latest_ai["confidence"] >= 0.70
    assert latest_ai["evidence_agreement"] >= 0.60
    assert latest_ai["review_required"] is False


def test_case_b_low_confidence_routes_to_verification_required(client: TestClient) -> None:
    """Case B: Low confidence routes to VERIFICATION_REQUIRED and review_required=True."""
    create_payload = {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address_hint": "Unknown corner",
        },
        "description": "something is weird here please look at it soon",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "uploads/unclear_photo.jpg",
                "file_hash": "b" * 64,
                "mime_type": "image/jpeg",
                "file_size_bytes": 102400,
            }
        ],
    }
    create_res = client.post("/api/v1/reports", json=create_payload)
    assert create_res.status_code == 201
    report_id = create_res.json()["id"]

    proc_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert proc_res.status_code == 202
    job_data = proc_res.json()

    assert job_data["status"] == "COMPLETED"
    assert job_data["review_required"] is True
    assert job_data["current_stage"] == "HUMAN_REVIEW"
    assert job_data["review_completed"] is False
    assert "LOW_CONFIDENCE" in (job_data["review_reason"] or "")

    get_res = client.get(f"/api/v1/reports/{report_id}")
    assert get_res.json()["status"] == "VERIFICATION_REQUIRED"


def test_case_c_modality_disagreement_routes_to_verification_required(client: TestClient) -> None:
    """Case C: Pothole image + streetlight failure text triggers MODALITY_DISAGREEMENT."""
    create_payload = {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address_hint": "Street 12 lamp post",
        },
        "description": "Streetlight pole broken and dark, lamp bulb shattered and not working.",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "uploads/cracked_asphalt_pothole.jpg",
                "file_hash": "c" * 64,
                "mime_type": "image/jpeg",
                "file_size_bytes": 1048576,
                "metadata_json": {"prototype_category": "Pothole"},
            }
        ],
    }
    create_res = client.post("/api/v1/reports", json=create_payload)
    assert create_res.status_code == 201
    report_id = create_res.json()["id"]

    proc_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert proc_res.status_code == 202
    job_data = proc_res.json()

    assert job_data["review_required"] is True
    assert job_data["current_stage"] == "HUMAN_REVIEW"
    assert "MODALITY_DISAGREEMENT" in (job_data["review_reason"] or "")

    get_res = client.get(f"/api/v1/reports/{report_id}")
    report_data = get_res.json()
    assert report_data["status"] == "VERIFICATION_REQUIRED"
    assert report_data["ai_analyses"][0]["evidence_agreement"] < 0.60


def test_case_d_intake_execution_records_clean_job(client: TestClient) -> None:
    """Case D: An intake execution records clean job events and advances through pipeline."""
    create_payload = {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address_hint": "North Gate",
        },
        "description": "Pothole on asphalt pavement needing patch repair.",
        "evidence": [],
    }
    create_res = client.post("/api/v1/reports", json=create_payload)
    assert create_res.status_code == 201
    report_id = create_res.json()["id"]

    proc_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert proc_res.status_code == 202
    assert proc_res.json()["status"] == "COMPLETED"


def test_case_e_reprocessing_preserves_history_and_creates_new_job(client: TestClient) -> None:
    """Case E: Reprocessing generates a new AIJob and keeps previous jobs and AIAnalyses."""
    create_payload = {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address_hint": "South Sector",
        },
        "description": "Water leak pipe burst gushing clean water into storm drain.",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "uploads/water_leak_pipe.jpg",
                "file_hash": "d" * 64,
                "mime_type": "image/jpeg",
                "file_size_bytes": 1048576,
                "metadata_json": {"prototype_category": "Water Leakage"},
            }
        ],
    }
    create_res = client.post("/api/v1/reports", json=create_payload)
    assert create_res.status_code == 201
    report_id = create_res.json()["id"]

    res1 = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert res1.status_code == 202
    job1_id = res1.json()["id"]

    res2 = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert res2.status_code == 202
    job2_id = res2.json()["id"]

    assert job1_id != job2_id

    jobs_res = client.get("/api/v1/ai/jobs")
    job_ids = [j["id"] for j in jobs_res.json()["items"]]
    assert job1_id in job_ids
    assert job2_id in job_ids

    report_res = client.get(f"/api/v1/reports/{report_id}")
    analyses = report_res.json()["ai_analyses"]
    assert len(analyses) == 3  # auto + 2 manual triggers


def test_case_f_human_verification_lifecycle(client: TestClient) -> None:
    """Case F: Human review closes gate, sets review_completed, and records audit event."""
    create_payload = {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address_hint": "East Avenue",
        },
        "description": "Uncertain electrical cable hanging low from utility pole.",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "uploads/cable_hanging.jpg",
                "file_hash": "e" * 64,
                "mime_type": "image/jpeg",
                "file_size_bytes": 500000,
            }
        ],
    }
    create_res = client.post("/api/v1/reports", json=create_payload)
    assert create_res.status_code == 201
    report_id = create_res.json()["id"]

    proc_res = client.post(f"/api/v1/reports/{report_id}/ai/process")
    assert proc_res.status_code == 202

    verify_payload = {
        "reviewer_id": "officer_sharma",
        "decision": "CORRECTED",
        "verified_category": "ELECTRICAL",
        "verified_severity": "CRITICAL",
        "notes": (
            "Verified in person: power line is active and poses imminent electrocution hazard."
        ),
    }
    verify_res = client.post(f"/api/v1/reports/{report_id}/verify", json=verify_payload)
    assert verify_res.status_code == 200
    verified_report = verify_res.json()
    assert verified_report["status"] == "VERIFIED"
    assert len(verified_report["verifications"]) == 1
    assert verified_report["verifications"][0]["decision"] == "CORRECTED"

    ai_res = client.get(f"/api/v1/reports/{report_id}/ai")
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    assert ai_data["latest_job"]["review_completed"] is True
    assert ai_data["verification"]["decision"] == "CORRECTED"

    events_res = client.get(f"/api/v1/reports/{report_id}/ai/events")
    assert events_res.status_code == 200
    events = events_res.json()
    stages = [e["stage"] for e in events]
    assert "HUMAN_REVIEW" in stages
    assert any(e["stage"] == "HUMAN_REVIEW" and e["status"] == "COMPLETED" for e in events)


def test_case_g_metrics_aggregation_and_thresholding(client: TestClient) -> None:
    """Case G: Metrics return real database counts and INSUFFICIENT_DATA when sample size < 5."""
    metrics_res = client.get("/api/v1/ai/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()

    assert metrics["total_jobs"]["display_state"] == "AVAILABLE"
    assert metrics["total_jobs"]["value"] >= 0
    assert metrics["completed_jobs"]["display_state"] == "AVAILABLE"
    assert metrics["failed_jobs"]["display_state"] == "AVAILABLE"
    assert metrics["active_jobs"]["display_state"] == "AVAILABLE"
    assert metrics["awaiting_human_review"]["display_state"] == "AVAILABLE"

    if metrics["completed_jobs"]["value"] > 0:
        assert metrics["avg_processing_latency_ms"]["display_state"] == "AVAILABLE"
        assert metrics["avg_processing_latency_ms"]["value"] is not None

    for metric_name in ["low_confidence_rate", "modality_disagreement_rate", "human_override_rate"]:
        m = metrics[metric_name]
        if m["sample_size"] < 5:
            assert m["value"] is None
            assert m["display_state"] == "INSUFFICIENT_DATA"
        else:
            assert m["value"] is not None
            assert m["display_state"] == "AVAILABLE"
