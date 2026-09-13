import base64

from fastapi.testclient import TestClient

# Minimal 1x1 valid JPEG bytes in base64
TINY_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
    b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)
TINY_JPEG_B64 = base64.b64encode(TINY_JPEG_BYTES).decode("ascii")


def test_create_report_with_citizen_identity_and_base64_image(client: TestClient) -> None:
    payload = {
        "location": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address_hint": "Brigade Road, Bengaluru",
        },
        "description": "Severe road cavity creating a traffic hazard.",
        "citizen_name": "Ramesh Kumar",
        "citizen_phone": "9876543210",
        "evidence": [
            {
                "evidence_type": "IMAGE",
                "storage_uri": "preview.jpg",
                "data_base64": TINY_JPEG_B64,
                "mime_type": "image/jpeg",
            }
        ],
    }

    # 1. Create Report
    response = client.post("/api/v1/reports", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()

    # 2. Verify Citizen Fields in Response
    assert data["citizen_name"] == "Ramesh Kumar"
    assert data["citizen_phone"] == "9876543210"

    # 3. Verify Stored Evidence
    assert len(data["evidences"]) == 1
    evidence = data["evidences"][0]
    storage_uri = evidence["storage_uri"]
    assert storage_uri.startswith("/uploads/rep_"), f"Unexpected storage_uri: {storage_uri}"
    assert storage_uri.endswith(".jpg")
    assert evidence["mime_type"] == "image/jpeg"
    assert evidence["file_size_bytes"] == len(TINY_JPEG_BYTES)

    # 4. Verify Static File Route Serves the Image
    img_resp = client.get(storage_uri)
    assert img_resp.status_code == 200
    assert img_resp.content == TINY_JPEG_BYTES
    assert "image/jpeg" in img_resp.headers["content-type"]

    # 5. Verify GET /api/v1/reports/{id} returns the same values
    get_resp = client.get(f"/api/v1/reports/{data['id']}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["citizen_name"] == "Ramesh Kumar"
    assert detail["citizen_phone"] == "9876543210"
    assert detail["evidences"][0]["storage_uri"] == storage_uri
