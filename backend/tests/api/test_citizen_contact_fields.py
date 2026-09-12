import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_report_with_all_citizen_fields() -> None:
    client_id = str(uuid.uuid4())
    payload = {
        "client_report_id": client_id,
        "location": {
            "latitude": 8.5241,
            "longitude": 76.9366,
            "address_hint": "Palayam, Thiruvananthapuram",
        },
        "description": "Large overflow of municipal waste bin near transit terminal",
        "citizen_name": "CivicSense Test User",
        "citizen_phone": "9874563210",
        "citizen_email": "civicsense.test@example.com",
        "citizen_postal_code": "695001",
    }

    res = client.post("/api/v1/reports", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["citizen_name"] == "CivicSense Test User"
    assert data["citizen_phone"] == "9874563210"
    assert data["citizen_email"] == "civicsense.test@example.com"
    assert data["citizen_postal_code"] == "695001"

    # Detail query should return all 4 fields for authorized triage
    report_id = data["id"]
    detail_res = client.get(f"/api/v1/reports/{report_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["citizen_name"] == "CivicSense Test User"
    assert detail["citizen_phone"] == "9874563210"
    assert detail["citizen_email"] == "civicsense.test@example.com"
    assert detail["citizen_postal_code"] == "695001"


def test_create_report_without_optional_email_and_postal_code() -> None:
    client_id = str(uuid.uuid4())
    payload = {
        "client_report_id": client_id,
        "location": {
            "latitude": 8.5241,
            "longitude": 76.9366,
        },
        "description": "Streetlight fixture loose and flickering continuously",
        "citizen_name": "Anonymous Citizen",
        "citizen_phone": "9876543210",
    }

    res = client.post("/api/v1/reports", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["citizen_name"] == "Anonymous Citizen"
    assert data["citizen_phone"] == "9876543210"
    assert data["citizen_email"] is None
    assert data["citizen_postal_code"] is None


def test_idempotent_replay_preserves_citizen_fields() -> None:
    client_id = str(uuid.uuid4())
    payload = {
        "client_report_id": client_id,
        "location": {
            "latitude": 8.5241,
            "longitude": 76.9366,
        },
        "description": "Damaged storm drain cover poses immediate pedestrian hazard",
        "citizen_name": "Idempotent Reporter",
        "citizen_phone": "9812345678",
        "citizen_email": "replay.test@example.com",
        "citizen_postal_code": "695002",
    }

    # Initial POST
    res1 = client.post("/api/v1/reports", json=payload)
    assert res1.status_code == 201

    # Replay POST
    res2 = client.post("/api/v1/reports", json=payload)
    assert res2.status_code == 200
    assert res2.headers.get("x-idempotent-replay") == "true"
    data2 = res2.json()
    assert data2["citizen_name"] == "Idempotent Reporter"
    assert data2["citizen_phone"] == "9812345678"
    assert data2["citizen_email"] == "replay.test@example.com"
    assert data2["citizen_postal_code"] == "695002"


def test_public_report_list_masks_private_contact_details() -> None:
    client_id = str(uuid.uuid4())
    payload = {
        "client_report_id": client_id,
        "location": {
            "latitude": 8.5241,
            "longitude": 76.9366,
        },
        "description": "Public list privacy verification report",
        "citizen_name": "Private Citizen",
        "citizen_phone": "9998887776",
        "citizen_email": "private.citizen@example.com",
        "citizen_postal_code": "695003",
    }

    create_res = client.post("/api/v1/reports", json=payload)
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # In public list feed, contact information must be masked
    list_res = client.get("/api/v1/reports?page=1&page_size=50")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    target = next((item for item in items if item["id"] == created_id), None)
    assert target is not None
    # Phone, email, postal code are strictly masked in public listing feeds
    assert target["citizen_phone"] is None
    assert target["citizen_email"] is None
    assert target["citizen_postal_code"] is None


def test_public_stats_omits_citizen_details() -> None:
    res = client.get("/api/v1/reports/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "totalReports" in stats
    assert "citizen_name" not in stats
    assert "citizen_phone" not in stats
    assert "citizen_email" not in stats
    assert "citizen_postal_code" not in stats


def test_create_report_with_explicit_category() -> None:
    client_id = str(uuid.uuid4())
    payload = {
        "client_report_id": client_id,
        "location": {
            "latitude": 8.5241,
            "longitude": 76.9366,
        },
        "description": "Deep asphalt trench across lane causing vehicle hazard",
        "category": "Road Damage",
        "citizen_name": "Category Tester",
    }

    res = client.post("/api/v1/reports", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["category"] == "Road Damage"

    # Verify detail retrieval returns category
    detail_res = client.get(f"/api/v1/reports/{data['id']}")
    assert detail_res.status_code == 200
    assert detail_res.json()["category"] == "Road Damage"

    # Verify list feed includes category
    list_res = client.get("/api/v1/reports?page=1&page_size=50")
    assert list_res.status_code == 200
    item = next((i for i in list_res.json()["items"] if i["id"] == data["id"]), None)
    assert item is not None
    assert item["category"] == "Road Damage"


def test_create_report_with_edge_category_hint_fallback() -> None:
    client_id = str(uuid.uuid4())
    payload = {
        "client_report_id": client_id,
        "location": {
            "latitude": 8.5241,
            "longitude": 76.9366,
        },
        "description": "Solid waste piled up next to storm canal",
        "edge_metadata": {
            "contract_version": "1.0.0",
            "client_processing": {
                "enabled": True,
                "processor_version": "1.0.0",
                "image_preprocessed": False,
                "text_preprocessed": True,
            },
            "category_hint": "Garbage",
        },
    }

    res = client.post("/api/v1/reports", json=payload)
    assert res.status_code == 201
    data = res.json()
    # Should fall back to category_hint from edge_metadata
    assert data["category"] == "Garbage"

