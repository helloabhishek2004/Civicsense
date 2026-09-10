import os
import subprocess
import sys
import time
import httpx

# Use SQLite for live local smoke test if PostgreSQL container is not up
os.environ["DATABASE_URL"] = "sqlite:///./live_verify.db"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from app.db.base import Base
from app.db.session import engine

# Ensure tables are created
Base.metadata.create_all(bind=engine)


def verify() -> None:
    # Start server as subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))

    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8888"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    base_url = "http://127.0.0.1:8888"
    client = httpx.Client(base_url=base_url, timeout=5.0)

    try:
        # Wait up to 10 seconds for server to come up
        started = False
        for _ in range(20):
            try:
                r = client.get("/health")
                if r.status_code == 200:
                    started = True
                    break
            except Exception:
                time.sleep(0.5)

        if not started:
            stdout, stderr = server_process.communicate(timeout=2)
            print("STDOUT:", stdout.decode())
            print("STDERR:", stderr.decode())
            raise RuntimeError("Server failed to start in time")

        print("--- 1. Testing GET /health ---")
        r1 = client.get("/health")
        print("Status:", r1.status_code, "Body:", r1.json(), "X-Request-ID:", r1.headers.get("X-Request-ID"))
        assert r1.status_code == 200

        print("\n--- 2. Testing GET /api/v1/health ---")
        r2 = client.get("/api/v1/health")
        print("Status:", r2.status_code, "Body:", r2.json(), "X-Request-ID:", r2.headers.get("X-Request-ID"))
        assert r2.status_code == 200

        print("\n--- 3. Testing GET /docs ---")
        r3 = client.get("/docs")
        print("Status:", r3.status_code, "Length:", len(r3.text))
        assert r3.status_code == 200

        print("\n--- 4. Testing GET /redoc ---")
        r4 = client.get("/redoc")
        print("Status:", r4.status_code, "Length:", len(r4.text))
        assert r4.status_code == 200

        print("\n--- 5. Testing POST /api/v1/reports ---")
        report_payload = {
            "location": {
                "latitude": 12.9249,
                "longitude": 77.4987,
                "address_hint": "Near Metro Pillar 42",
            },
            "description": "Severe road surface damage and water accumulation near transit station.",
            "citizen_id": "citizen_live_verify_001",
            "evidence": [
                {
                    "evidence_type": "IMAGE",
                    "storage_uri": "uploads/live_test_img.jpg",
                    "mime_type": "image/jpeg",
                    "file_size_bytes": 102400,
                }
            ],
        }
        r5 = client.post("/api/v1/reports", json=report_payload)
        print("Status:", r5.status_code, "Body:", r5.json(), "X-Request-ID:", r5.headers.get("X-Request-ID"))
        assert r5.status_code == 201
        created_data = r5.json()
        report_id = created_data["id"]
        tracking_id = created_data["tracking_id"]

        print("\n--- 6. Testing GET /api/v1/reports ---")
        r6 = client.get("/api/v1/reports?page=1&page_size=10")
        print("Status:", r6.status_code, "Total:", r6.json().get("total"), "Items:", len(r6.json().get("items")))
        assert r6.status_code == 200

        print("\n--- 7. Testing GET /api/v1/reports/{id} by UUID ---")
        r7_uuid = client.get(f"/api/v1/reports/{report_id}")
        print("Status:", r7_uuid.status_code, "Tracking ID:", r7_uuid.json().get("tracking_id"))
        assert r7_uuid.status_code == 200

        print("\n--- 8. Testing GET /api/v1/reports/{tracking_id} by Tracking ID ---")
        r7_tracking = client.get(f"/api/v1/reports/{tracking_id}")
        print("Status:", r7_tracking.status_code, "UUID:", r7_tracking.json().get("id"))
        assert r7_tracking.status_code == 200

        print("\n===> ALL LIVE API VERIFICATION CHECKS PASSED SUCCESSFULLY! <===")
    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except Exception:
            server_process.kill()


if __name__ == "__main__":
    verify()
