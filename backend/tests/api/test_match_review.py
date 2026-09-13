"""API tests for the match review workflow endpoints.

Tests cover: listing pending matches, approval, rejection, authorization,
invalid IDs, repeated review actions, and audit trail integrity.
"""

import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.issue import Issue
from app.models.report import Report
from app.models.report_issue_match import ReportIssueMatch


def _create_pending_candidate(
    db: Session,
    *,
    lat: float = 12.9716,
    lon: float = 77.5946,
    category: str = "Pothole",
) -> tuple[Report, Issue, ReportIssueMatch]:
    """Helper to create a report, issue, and PENDING CANDIDATE match."""
    issue = Issue(
        id=uuid.uuid4(),
        title=f"{category}: Test issue",
        category=category,
        status="OPEN",
        primary_latitude=lat,
        primary_longitude=lon,
        report_count=1,
    )
    db.add(issue)

    report = Report(
        id=uuid.uuid4(),
        tracking_id=f"REP-MATCH-{uuid.uuid4().hex[:6].upper()}",
        status="SUBMITTED",
        latitude=lat + 0.0001,
        longitude=lon + 0.0001,
        category=category,
        description=f"Test report for match review: {category}",
        citizen_id="test-citizen",
    )
    db.add(report)

    record = ReportIssueMatch(
        id=uuid.uuid4(),
        report_id=report.id,
        issue_id=issue.id,
        action="CANDIDATE",
        status="PENDING",
        combined_score=0.55,
        text_similarity=0.40,
        distance_meters=15.0,
        category_match=1.0,
        reasoning=["test candidate match"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return report, issue, record


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------

class TestMatchReviewAuth:
    def test_list_pending_requires_reviewer_header(self, client: TestClient) -> None:
        """GET /matches/pending without X-Reviewer-ID returns 401."""
        resp = client.get("/api/v1/matches/pending")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_approve_requires_reviewer_header(self, client: TestClient) -> None:
        """POST /matches/{id}/approve without X-Reviewer-ID returns 401."""
        resp = client.post(
            f"/api/v1/matches/{uuid.uuid4()}/approve",
            json={"reviewer_id": "officer-1"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_reject_requires_reviewer_header(self, client: TestClient) -> None:
        """POST /matches/{id}/reject without X-Reviewer-ID returns 401."""
        resp = client.post(
            f"/api/v1/matches/{uuid.uuid4()}/reject",
            json={"reviewer_id": "officer-1"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_approve_rejects_empty_reviewer_header(self, client: TestClient) -> None:
        """Empty X-Reviewer-ID header returns 401."""
        resp = client.post(
            f"/api/v1/matches/{uuid.uuid4()}/approve",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": ""},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_approve_rejects_reviewer_id_mismatch(self, client: TestClient, db_session: Session) -> None:
        """X-Reviewer-ID header must match body reviewer_id."""
        _, _, record = _create_pending_candidate(db_session)
        resp = client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-A"},
            headers={"X-Reviewer-ID": "officer-B"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# List pending matches
# ---------------------------------------------------------------------------

class TestListPendingMatches:
    def test_list_empty_when_no_pending(self, client: TestClient) -> None:
        """No pending matches returns empty list."""
        resp = client.get(
            "/api/v1/matches/pending",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_returns_pending_matches(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Pending matches are returned with correct structure."""
        report, issue, record = _create_pending_candidate(db_session)
        resp = client.get(
            "/api/v1/matches/pending",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["id"] == str(record.id)
        assert item["report_id"] == str(report.id)
        assert item["issue_id"] == str(issue.id)
        assert item["action"] == "CANDIDATE"
        assert item["status"] == "PENDING"
        assert item["combined_score"] == 0.55

    def test_list_pagination(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Pagination parameters are respected."""
        _create_pending_candidate(db_session)
        _create_pending_candidate(db_session)
        resp = client.get(
            "/api/v1/matches/pending?page=1&page_size=1",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 2


# ---------------------------------------------------------------------------
# Approve match
# ---------------------------------------------------------------------------

class TestApproveMatch:
    def test_approve_links_report_to_issue(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Approving a candidate links the report to the candidate issue."""
        report, issue, record = _create_pending_candidate(db_session)
        resp = client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-1", "notes": "Confirmed duplicate"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "APPROVED"
        assert data["report_id"] == str(report.id)
        assert data["issue_id"] == str(issue.id)
        assert data["reviewer_id"] == "officer-1"
        assert data["reviewed_at"] is not None

    def test_approve_increments_issue_report_count(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Approval increments the issue's report_count."""
        report, issue, record = _create_pending_candidate(db_session)
        db_session.refresh(issue)
        count_before = issue.report_count

        client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        db_session.refresh(issue)
        assert issue.report_count == count_before + 1

    def test_approve_nonexistent_match_returns_404(
        self, client: TestClient
    ) -> None:
        """Approving a non-existent match returns 404."""
        resp = client.post(
            f"/api/v1/matches/{uuid.uuid4()}/approve",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_approve_already_approved(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Approving an already-approved match returns 409 MATCH_ALREADY_REVIEWED."""
        _, _, record = _create_pending_candidate(db_session)
        client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        resp = client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-2"},
            headers={"X-Reviewer-ID": "officer-2"},
        )
        assert resp.status_code == status.HTTP_409_CONFLICT
        data = resp.json()
        assert data["detail"]["code"] == "MATCH_ALREADY_REVIEWED"

    def test_approve_supersedes_other_pending_matches(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Approval supersedes other PENDING matches for the same report."""
        report, issue, record = _create_pending_candidate(db_session)
        other_record = ReportIssueMatch(
            report_id=report.id,
            issue_id=uuid.uuid4(),
            action="CANDIDATE",
            status="PENDING",
            combined_score=0.50,
            text_similarity=0.30,
            distance_meters=10.0,
            category_match=0.5,
        )
        db_session.add(other_record)
        db_session.commit()

        client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        db_session.refresh(other_record)
        assert other_record.status == "SUPERSEDED"


# ---------------------------------------------------------------------------
# Reject match
# ---------------------------------------------------------------------------

class TestRejectMatch:
    def test_reject_leaves_report_unlinked(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Rejecting a candidate leaves the report unlinked."""
        report, issue, record = _create_pending_candidate(db_session)
        resp = client.post(
            f"/api/v1/matches/{record.id}/reject",
            json={"reviewer_id": "officer-1", "notes": "Not a duplicate"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert data["report_id"] == str(report.id)
        assert data["reviewer_id"] == "officer-1"
        assert data["reviewed_at"] is not None

    def test_reject_nonexistent_match_returns_404(
        self, client: TestClient
    ) -> None:
        """Rejecting a non-existent match returns 404."""
        resp = client.post(
            f"/api/v1/matches/{uuid.uuid4()}/reject",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_reject_already_rejected(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Rejecting an already-rejected match returns 409 MATCH_ALREADY_REVIEWED."""
        _, _, record = _create_pending_candidate(db_session)
        client.post(
            f"/api/v1/matches/{record.id}/reject",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        resp = client.post(
            f"/api/v1/matches/{record.id}/reject",
            json={"reviewer_id": "officer-2"},
            headers={"X-Reviewer-ID": "officer-2"},
        )
        assert resp.status_code == status.HTTP_409_CONFLICT
        data = resp.json()
        assert data["detail"]["code"] == "MATCH_ALREADY_REVIEWED"

    def test_reject_with_alternate_issue_link(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Rejecting with link_to_issue_id links report to the alternate issue."""
        report, issue, record = _create_pending_candidate(db_session)

        alternate_issue = Issue(
            id=uuid.uuid4(),
            title="Alternate issue",
            category="Pothole",
            status="OPEN",
            primary_latitude=12.9716,
            primary_longitude=77.5946,
            report_count=1,
        )
        db_session.add(alternate_issue)
        db_session.commit()

        resp = client.post(
            f"/api/v1/matches/{record.id}/reject",
            json={
                "reviewer_id": "officer-1",
                "link_to_issue_id": str(alternate_issue.id),
            },
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert data["issue_id"] == str(alternate_issue.id)

    def test_reject_supersedes_other_pending_matches(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Rejection supersedes other PENDING matches for the same report."""
        report, issue, record = _create_pending_candidate(db_session)
        other_record = ReportIssueMatch(
            report_id=report.id,
            issue_id=uuid.uuid4(),
            action="CANDIDATE",
            status="PENDING",
            combined_score=0.50,
            text_similarity=0.30,
            distance_meters=10.0,
            category_match=0.5,
        )
        db_session.add(other_record)
        db_session.commit()

        client.post(
            f"/api/v1/matches/{record.id}/reject",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        db_session.refresh(other_record)
        assert other_record.status == "SUPERSEDED"


# ---------------------------------------------------------------------------
# Audit trail integrity
# ---------------------------------------------------------------------------

class TestMatchReviewAuditTrail:
    def test_approval_preserves_audit_fields(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Approval sets reviewed_at, reviewer_id, and notes."""
        _, _, record = _create_pending_candidate(db_session)
        client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-1", "notes": "Confirmed dup"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        db_session.refresh(record)
        assert record.status == "APPROVED"
        assert record.reviewer_id == "officer-1"
        assert record.reviewed_at is not None
        assert record.review_notes == "Confirmed dup"

    def test_rejection_preserves_audit_fields(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Rejection sets reviewed_at, reviewer_id, and notes."""
        _, _, record = _create_pending_candidate(db_session)
        client.post(
            f"/api/v1/matches/{record.id}/reject",
            json={"reviewer_id": "officer-1", "notes": "Not a dup"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        db_session.refresh(record)
        assert record.status == "REJECTED"
        assert record.reviewer_id == "officer-1"
        assert record.reviewed_at is not None
        assert record.review_notes == "Not a dup"

    def test_pending_match_retains_full_metadata(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Pending match shows all scoring metadata in list endpoint."""
        report, issue, record = _create_pending_candidate(db_session)
        resp = client.get(
            "/api/v1/matches/pending",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        item = resp.json()["items"][0]
        assert item["text_similarity"] == 0.40
        assert item["distance_meters"] == 15.0
        assert item["category_match"] == 1.0
        assert item["combined_score"] == 0.55
        assert item["reasoning"] == ["test candidate match"]

    def test_list_matches_with_status_filter(
        self, client: TestClient, db_session: Session
    ) -> None:
        """GET /matches with status filter returns audited records."""
        _, _, record = _create_pending_candidate(db_session)
        # Approve the record
        client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-1", "notes": "Audit test"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        # Query approved matches
        resp = client.get(
            "/api/v1/matches?status=APPROVED",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["total"] >= 1
        ids = [m["id"] for m in data["items"]]
        assert str(record.id) in ids

    def test_get_match_by_id_audit_detail(
        self, client: TestClient, db_session: Session
    ) -> None:
        """GET /matches/{id} retrieves complete audit details."""
        _, _, record = _create_pending_candidate(db_session)
        client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-1", "notes": "Audited decision"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        resp = client.get(
            f"/api/v1/matches/{record.id}",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == str(record.id)
        assert data["status"] == "APPROVED"
        assert data["reviewer_id"] == "officer-1"
        assert data["review_notes"] == "Audited decision"
        assert data["reviewed_at"] is not None

    def test_get_nonexistent_match_returns_404(self, client: TestClient) -> None:
        """GET /matches/{id} for non-existent match returns 404."""
        resp = client.get(
            f"/api/v1/matches/{uuid.uuid4()}",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 409 Conflict and state immutability
# ---------------------------------------------------------------------------


class TestRepeatReview409Immutability:
    def test_approve_then_reject_returns_409(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Attempting to reject an already-approved match returns 409."""
        _, _, record = _create_pending_candidate(db_session)
        client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        resp = client.post(
            f"/api/v1/matches/{record.id}/reject",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.json()["detail"]["code"] == "MATCH_ALREADY_REVIEWED"

    def test_409_does_not_alter_database_state(
        self, client: TestClient, db_session: Session
    ) -> None:
        """After a 409 repeat-review the match record is unchanged in the database."""
        _, _, record = _create_pending_candidate(db_session)
        client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-1", "notes": "First review"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        db_session.refresh(record)
        first_reviewer = record.reviewer_id
        first_notes = record.review_notes

        # Attempt second review — 409, nothing should change
        client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-2", "notes": "Attempted overwrite"},
            headers={"X-Reviewer-ID": "officer-2"},
        )
        db_session.refresh(record)
        assert record.status == "APPROVED"
        assert record.reviewer_id == first_reviewer
        assert record.review_notes == first_notes

    def test_reject_then_approve_returns_409(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Attempting to approve an already-rejected match returns 409."""
        _, _, record = _create_pending_candidate(db_session)
        client.post(
            f"/api/v1/matches/{record.id}/reject",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        resp = client.post(
            f"/api/v1/matches/{record.id}/approve",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.json()["detail"]["code"] == "MATCH_ALREADY_REVIEWED"


# ---------------------------------------------------------------------------
# Match list filtering and pagination
# ---------------------------------------------------------------------------


class TestMatchListFiltering:
    def test_filter_by_report_id(
        self, client: TestClient, db_session: Session
    ) -> None:
        """GET /matches?report_id=... filters to a specific report."""
        report, _, _record = _create_pending_candidate(db_session)
        _create_pending_candidate(db_session)  # unrelated record
        resp = client.get(
            f"/api/v1/matches?report_id={report.id}",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["report_id"] == str(report.id)

    def test_filter_by_issue_id(
        self, client: TestClient, db_session: Session
    ) -> None:
        """GET /matches?issue_id=... filters to a specific issue."""
        _, issue, _record = _create_pending_candidate(db_session)
        _create_pending_candidate(db_session)
        resp = client.get(
            f"/api/v1/matches?issue_id={issue.id}",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["issue_id"] == str(issue.id)

    def test_filter_rejected_status(
        self, client: TestClient, db_session: Session
    ) -> None:
        """GET /matches?status=REJECTED returns only rejected matches."""
        _, _, record = _create_pending_candidate(db_session)
        client.post(
            f"/api/v1/matches/{record.id}/reject",
            json={"reviewer_id": "officer-1"},
            headers={"X-Reviewer-ID": "officer-1"},
        )
        resp = client.get(
            "/api/v1/matches?status=REJECTED",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(m["status"] == "REJECTED" for m in data["items"])
        assert data["total"] >= 1

    def test_pagination_page_size(
        self, client: TestClient, db_session: Session
    ) -> None:
        """GET /matches with page_size=1 returns exactly 1 item."""
        _create_pending_candidate(db_session)
        _create_pending_candidate(db_session)
        resp = client.get(
            "/api/v1/matches?page=1&page_size=1",
            headers={"X-Reviewer-ID": "officer-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] >= 2

    def test_list_matches_requires_reviewer_header(
        self, client: TestClient
    ) -> None:
        """GET /matches without X-Reviewer-ID returns 401."""
        resp = client.get("/api/v1/matches")
        assert resp.status_code == 401

