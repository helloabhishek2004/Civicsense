import uuid

from fastapi.testclient import TestClient


def test_citizen_report_sync_filtering(client: TestClient) -> None:
    """Test citizen_id filtering on GET /api/v1/reports."""
    citizen_a = f"czn_{uuid.uuid4()}"
    citizen_b = f"czn_{uuid.uuid4()}"

    # 1. Create reports for Citizen A
    report_a_payload = {
        "location": {"latitude": 8.5615, "longitude": 76.8850, "address_hint": "Location A"},
        "description": "Report for citizen A - damaged road",
        "category": "Road Damage",
        "citizen_id": citizen_a,
        "citizen_name": "Citizen A",
        "citizen_phone": "9876543210",
        "citizen_email": "citizen.a@example.com",
        "citizen_postal_code": "695001",
    }
    resp_a = client.post("/api/v1/reports", json=report_a_payload)
    assert resp_a.status_code == 201
    created_a = resp_a.json()
    tracking_id_a = created_a["tracking_id"]
    assert created_a["citizen_id"] == citizen_a

    # 2. Create reports for Citizen B
    report_b_payload = {
        "location": {"latitude": 8.5690, "longitude": 76.8710, "address_hint": "Location B"},
        "description": "Report for citizen B - waste dumping",
        "category": "Garbage",
        "citizen_id": citizen_b,
        "citizen_name": "Citizen B",
        "citizen_phone": "9876543211",
        "citizen_email": "citizen.b@example.com",
        "citizen_postal_code": "695002",
    }
    resp_b = client.post("/api/v1/reports", json=report_b_payload)
    assert resp_b.status_code == 201
    created_b = resp_b.json()
    tracking_id_b = created_b["tracking_id"]

    # 3. Query reports for Citizen A
    list_a = client.get(f"/api/v1/reports?citizen_id={citizen_a}")
    assert list_a.status_code == 200
    data_a = list_a.json()
    items_a = data_a["items"]
    assert any(r["tracking_id"] == tracking_id_a for r in items_a)
    assert not any(r["tracking_id"] == tracking_id_b for r in items_a)

    # Verify contact privacy stripping in list
    item_a = next(r for r in items_a if r["tracking_id"] == tracking_id_a)
    assert item_a["citizen_phone"] is None
    assert item_a["citizen_email"] is None
    assert item_a["citizen_postal_code"] is None
    assert item_a["citizen_id"] == citizen_a

    # 4. Query reports for Citizen B
    list_b = client.get(f"/api/v1/reports?citizen_id={citizen_b}")
    assert list_b.status_code == 200
    data_b = list_b.json()
    items_b = data_b["items"]
    assert any(r["tracking_id"] == tracking_id_b for r in items_b)
    assert not any(r["tracking_id"] == tracking_id_a for r in items_b)

    # 5. Query for unknown citizen returns empty list
    unknown_citizen = f"czn_{uuid.uuid4()}"
    list_unknown = client.get(f"/api/v1/reports?citizen_id={unknown_citizen}")
    assert list_unknown.status_code == 200
    data_unknown = list_unknown.json()
    assert data_unknown["total"] == 0
    assert len(data_unknown["items"]) == 0

    # 6. Query without citizen_id returns both (dashboard behavior)
    list_all = client.get("/api/v1/reports")
    assert list_all.status_code == 200
    data_all = list_all.json()
    items_all = data_all["items"]
    assert any(r["tracking_id"] == tracking_id_a for r in items_all)
    assert any(r["tracking_id"] == tracking_id_b for r in items_all)

    # 7. Single report detail returns complete report
    detail = client.get(f"/api/v1/reports/{tracking_id_a}")
    assert detail.status_code == 200
    detail_data = detail.json()
    assert detail_data["tracking_id"] == tracking_id_a
    assert detail_data["citizen_id"] == citizen_a
    assert detail_data["category"] == "Road Damage"
    assert detail_data["status"] == "SUBMITTED"
