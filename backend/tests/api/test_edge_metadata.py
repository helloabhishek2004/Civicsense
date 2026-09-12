"""Tests for edge-processing metadata ingestion, validation, and backward compatibility."""

import uuid

from fastapi import status
from fastapi.testclient import TestClient


def test_create_report_with_edge_metadata(client: TestClient) -> None:
    """Validate full edge-processing metadata package ingestion and persistence."""
    client_uuid = str(uuid.uuid4())
    payload = {
        "location": {
            "latitude": 8.5241,
            "longitude": 76.9366,
            "accuracy_meters": 12.5,
            "address_hint": "Palayam, Trivandrum",
        },
        "description": "Large deep pothole near the bus stop causing traffic congestion",
        "citizen_id": "cit_edge_test_123",
        "client_report_id": client_uuid,
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "cache/previews/preview_test_123.jpg",
                "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "mime_type": "image/jpeg",
                "file_size_bytes": 48231,
                "metadata_json": {
                    "is_preview": True,
                    "width": 640,
                    "height": 480,
                },
            }
        ],
        "edge_metadata": {
            "contract_version": "1.0.0",
            "client_processing": {
                "enabled": True,
                "processor_version": "1.0.0",
                "image_preprocessed": True,
                "text_preprocessed": True,
                "embedding_generated": False,
            },
            "image_quality": {
                "width": 640,
                "height": 480,
                "aspect_ratio": 1.333,
                "file_size_bytes": 48231,
                "mime_type": "image/jpeg",
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "brightness": 0.61,
                "is_blurry": False,
                "usable": True,
                "feedback_message": "The image looks good and sharp.",
            },
            "text_features": {
                "raw_text": "Large deep pothole near the bus stop causing traffic congestion",
                "cleaned_text": "Large deep pothole near the bus stop causing traffic congestion",
                "character_count": 63,
                "word_count": 10,
                "language": "en",
                "severity_terms": ["large", "deep"],
                "urgency_terms": [],
                "category_terms": ["pothole"],
                "location_terms": ["near", "bus stop"],
                "safety_terms": ["traffic"],
            },
            "category_hint": "pothole",
            "embedding": None,
        },
    }

    response = client.post("/api/v1/reports", json=payload)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()

    assert data["id"] == client_uuid
    assert data["status"] == "SUBMITTED"
    assert data["edge_metadata"] is not None
    assert data["edge_metadata"]["contract_version"] == "1.0.0"
    assert data["edge_metadata"]["client_processing"]["processor_version"] == "1.0.0"
    assert data["edge_metadata"]["image_quality"]["width"] == 640
    assert data["edge_metadata"]["text_features"]["word_count"] == 10
    assert "pothole" in data["edge_metadata"]["text_features"]["category_terms"]

    # Verify retrieval preserves edge metadata
    get_res = client.get(f"/api/v1/reports/{data['tracking_id']}")
    assert get_res.status_code == status.HTTP_200_OK
    fetched = get_res.json()
    assert fetched["edge_metadata"] is not None
    expected_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert fetched["edge_metadata"]["image_quality"]["sha256"] == expected_hash

    # Trigger AI processing on edge-preprocessed report and verify stage 2 audit
    ai_process_res = client.post(f"/api/v1/reports/{data['tracking_id']}/ai/process")
    assert ai_process_res.status_code == status.HTTP_202_ACCEPTED

    events_res = client.get(f"/api/v1/reports/{data['tracking_id']}/ai/events")
    assert events_res.status_code == status.HTTP_200_OK
    events = events_res.json()
    prep_event = next(e for e in events if e["stage"] == "PREPROCESSING")
    assert prep_event["metadata_json"]["edge_preprocessed"] is True
    assert prep_event["metadata_json"]["client_processor_version"] == "1.0.0"


def test_backward_compatibility_report_without_edge_metadata(client: TestClient) -> None:
    """Confirm report submission without edge metadata succeeds without failure."""
    payload = {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
        "description": "Broken sidewalk tile near government office",
    }
    response = client.post("/api/v1/reports", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["edge_metadata"] is None

    # AI processing continues to work cleanly
    ai_res = client.post(f"/api/v1/reports/{data['id']}/ai/process")
    assert ai_res.status_code == status.HTTP_202_ACCEPTED
    events_res = client.get(f"/api/v1/reports/{data['id']}/ai/events")
    events = events_res.json()
    prep_event = next(e for e in events if e["stage"] == "PREPROCESSING")
    assert prep_event["metadata_json"]["edge_preprocessed"] is False


def test_invalid_edge_metadata_rejected(client: TestClient) -> None:
    """Confirm server-side validation rejects invalid edge metadata formats."""
    # Invalid sha256 (not 64 chars) and invalid brightness (> 1.0)
    payload = {
        "location": {
            "latitude": 8.5241,
            "longitude": 76.9366,
        },
        "description": "Streetlight broken and sparking",
        "edge_metadata": {
            "client_processing": {
                "enabled": True,
                "processor_version": "1.0.0",
            },
            "image_quality": {
                "width": 640,
                "height": 480,
                "aspect_ratio": 1.33,
                "file_size_bytes": 1000,
                "mime_type": "image/jpeg",
                "sha256": "invalid_short_hash",
                "brightness": 1.5,  # Out of range (0.0 to 1.0)
            },
        },
    }
    response = client.post("/api/v1/reports", json=payload)
    assert response.status_code in (status.HTTP_422_UNPROCESSABLE_ENTITY, 422)
