from fastapi.testclient import TestClient


def test_list_and_get_departments(client: TestClient) -> None:
    # 1. List departments
    res = client.get("/api/v1/departments")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 6
    roads_dept = next((d for d in data if d["code"] == "ROADS"), None)
    assert roads_dept is not None
    assert roads_dept["name"] == "Roads & Bridges"
    assert "stats" in roads_dept

    # 2. Get department by code
    res_code = client.get("/api/v1/departments/ROADS")
    assert res_code.status_code == 200
    assert res_code.json()["id"] == roads_dept["id"]

    # 3. Get department by UUID
    res_id = client.get(f"/api/v1/departments/{roads_dept['id']}")
    assert res_id.status_code == 200
    assert res_id.json()["code"] == "ROADS"

    # 4. Get stats
    res_stats = client.get("/api/v1/departments/ROADS/stats")
    assert res_stats.status_code == 200
    assert res_stats.json()["department_code"] == "ROADS"


def test_department_assignment_and_lifecycle_flow(client: TestClient) -> None:
    # Step 1: Create a report (SUBMITTED)
    create_payload = {
        "location": {"latitude": 12.9716, "longitude": 77.5946, "address_hint": "MG Road"},
        "description": "Large road crater causing vehicle damage and traffic bottleneck",
        "category": "Pothole",
        "citizen_name": "Test Citizen",
        "citizen_phone": "9998887776",
    }
    r_res = client.post("/api/v1/reports", json=create_payload)
    assert r_res.status_code == 201
    report_id = r_res.json()["id"]

    # Step 2: Verification (SUBMITTED -> VERIFIED)
    v_res = client.post(
        f"/api/v1/reports/{report_id}/verify",
        json={
            "reviewer_id": "officer_sharma",
            "decision": "CONFIRMED",
            "verified_category": "Road Damage",
            "verified_severity": "HIGH",
            "notes": "Verified severe crater on MG Road",
        },
    )
    assert v_res.status_code == 200
    assert v_res.json()["status"] == "VERIFIED"

    # Step 3: Prioritization (VERIFIED -> PRIORITIZED)
    p_res = client.patch(
        f"/api/v1/reports/{report_id}/transition",
        json={"next_status": "PRIORITIZED", "priority": "HIGH"},
    )
    assert p_res.status_code == 200
    assert p_res.json()["status"] == "PRIORITIZED"

    # Step 4: Assign to Roads & Bridges Department (PRIORITIZED -> ASSIGNED)
    assign_payload = {
        "department_name": "Roads & Bridges",
        "assigned_by": "Chief Dispatcher",
        "assigned_to_officer": "Eng. Rajesh",
        "notes": "Dispatch repair crew unit 4 immediately",
    }
    a_res = client.post(f"/api/v1/reports/{report_id}/assign", json=assign_payload)
    assert a_res.status_code == 200
    rep_assigned = a_res.json()
    assert rep_assigned["status"] == "ASSIGNED"
    assert rep_assigned["department"] == "Roads & Bridges"
    assert rep_assigned["department_id"] is not None
    assert rep_assigned["assigned_officer"] == "Eng. Rajesh"
    assert rep_assigned["reassignment_required"] is False
    assert len(rep_assigned["assignments"]) == 1
    assert rep_assigned["assignments"][0]["status"] == "ASSIGNED"
    assert rep_assigned["current_assignment"]["status"] == "ASSIGNED"

    # Step 5: Department acknowledges job (ASSIGNED -> IN_PROGRESS)
    ack_payload = {
        "assigned_to_officer": "Eng. Rajesh",
        "notes": "Crew mobilized with asphalt patching truck",
    }
    ack_res = client.post(f"/api/v1/reports/{report_id}/acknowledge", json=ack_payload)
    assert ack_res.status_code == 200
    rep_acked = ack_res.json()
    assert rep_acked["status"] == "IN_PROGRESS"
    assert rep_acked["current_assignment"]["status"] == "IN_PROGRESS"

    # Step 6: Department marks work completed (IN_PROGRESS -> RESOLVED)
    comp_payload = {
        "resolver_notes": "Filled crater with cold-mix asphalt and compacted with roller",
        "resolved_by": "Eng. Rajesh",
    }
    comp_res = client.post(f"/api/v1/reports/{report_id}/complete", json=comp_payload)
    assert comp_res.status_code == 200
    rep_comp = comp_res.json()
    assert rep_comp["status"] == "RESOLVED"
    assert rep_comp["current_assignment"]["status"] == "COMPLETED"
    assert rep_comp["current_assignment"]["resolved_at"] is not None

    # Step 7: Check assignment audit history
    hist_res = client.get(f"/api/v1/reports/{report_id}/assignments")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 1
    assert history[0]["status"] == "COMPLETED"

    # Step 8: Check department reports listing
    dept_reports_res = client.get("/api/v1/departments/ROADS/reports")
    assert dept_reports_res.status_code == 200
    dept_reports = dept_reports_res.json()
    assert dept_reports["total"] >= 1
    assert dept_reports["items"][0]["id"] == report_id


def test_department_rejection_routing_flow(client: TestClient) -> None:
    # Create report and fast-forward to PRIORITIZED
    r_res = client.post(
        "/api/v1/reports",
        json={
            "location": {"latitude": 12.9716, "longitude": 77.5946},
            "description": "Leaking high pressure water valve flooding electrical junction box",
            "category": "Water Leakage",
        },
    )
    report_id = r_res.json()["id"]
    client.post(
        f"/api/v1/reports/{report_id}/verify",
        json={"decision": "CONFIRMED", "notes": "Verified water flooding"},
    )
    client.patch(
        f"/api/v1/reports/{report_id}/transition",
        json={"next_status": "PRIORITIZED"},
    )

    # Accidentally assign to Street Lighting & Electrical
    client.post(
        f"/api/v1/reports/{report_id}/assign",
        json={"department_name": "Street Lighting & Electrical", "notes": "Initial assignment"},
    )

    # Department rejects because it's a water main burst (OUT_OF_JURISDICTION)
    reject_payload = {
        "rejection_reason": "OUT_OF_JURISDICTION",
        "notes": (
            "Flooding caused by broken water line; requires Water Supply & Sewerage crew first."
        ),
        "suggested_department": "Water Supply & Sewerage",
    }
    rej_res = client.post(f"/api/v1/reports/{report_id}/department-reject", json=reject_payload)
    assert rej_res.status_code == 200
    rep_rej = rej_res.json()

    # Rejection returns to PRIORITIZED (NOT closed!)
    assert rep_rej["status"] == "PRIORITIZED"
    assert rep_rej["reassignment_required"] is True
    # Department reference preserved for history
    assert rep_rej["department"] == "Street Lighting & Electrical"

    # Verify assignment record marked REJECTED with reason and notes
    assert len(rep_rej["assignments"]) == 1
    assignment = rep_rej["assignments"][0]
    assert assignment["status"] == "REJECTED"
    assert assignment["rejection_reason"] == "OUT_OF_JURISDICTION"
    assert "Flooding caused by broken water line" in assignment["notes"]

    # Re-assign to Water Supply & Sewerage
    reassign_payload = {
        "department_name": "Water Supply & Sewerage",
        "assigned_by": "Re-Triage Admin",
        "notes": "Reassigned following electrical department review",
    }
    reassign_res = client.post(f"/api/v1/reports/{report_id}/assign", json=reassign_payload)
    assert reassign_res.status_code == 200
    rep_reassigned = reassign_res.json()
    assert rep_reassigned["status"] == "ASSIGNED"
    assert rep_reassigned["department"] == "Water Supply & Sewerage"
    assert rep_reassigned["reassignment_required"] is False
    # Now there should be 2 historical assignments
    assert len(rep_reassigned["assignments"]) == 2
    assert rep_reassigned["assignments"][0]["status"] == "ASSIGNED"
    assert rep_reassigned["assignments"][1]["status"] == "REJECTED"
