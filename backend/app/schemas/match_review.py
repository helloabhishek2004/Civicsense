"""Schemas for the match review workflow (dedup candidate approve/reject)."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.common import ensure_utc


class MatchComponentRead(BaseModel):
    """Readable component scores for a similarity match."""

    text_similarity: float
    distance_meters: float
    category_match: float

    model_config = ConfigDict(from_attributes=True)


class MatchRead(BaseModel):
    """Readable representation of a ReportIssueMatch for API consumers."""

    id: uuid.UUID
    report_id: uuid.UUID
    issue_id: uuid.UUID | None = None
    action: str
    status: str
    combined_score: float
    text_similarity: float
    distance_meters: float
    category_match: float
    reasoning: list[str] | None = None
    embedding_model_version: str | None = None
    reviewed_at: datetime.datetime | None = None
    reviewer_id: str | None = None
    review_notes: str | None = None
    created_at: datetime.datetime

    @field_validator("created_at", "reviewed_at", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        return ensure_utc(v)

    @field_serializer("created_at", "reviewed_at", when_used="json-unless-none")
    def serialize_utc(self, v: datetime.datetime | None) -> str | None:
        if v is None:
            return None
        res = ensure_utc(v)
        assert res is not None
        return res.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)


class MatchListResponse(BaseModel):
    """Paginated list of match review records."""

    items: list[MatchRead]
    total: int
    page: int
    page_size: int


class ApproveRequest(BaseModel):
    """Payload for approving a candidate match."""

    reviewer_id: str = Field(
        ..., min_length=1, max_length=128,
        description="Municipal reviewer identifier",
    )
    notes: str | None = Field(
        None, max_length=512, description="Optional reviewer notes",
    )


class RejectRequest(BaseModel):
    """Payload for rejecting a candidate match."""

    reviewer_id: str = Field(
        ..., min_length=1, max_length=128,
        description="Municipal reviewer identifier",
    )
    notes: str | None = Field(
        None, max_length=512, description="Optional rejection reason",
    )
    link_to_issue_id: uuid.UUID | None = Field(
        None, description="If provided, link report to this issue instead"
    )


class UnifiedReviewRequest(BaseModel):
    """Payload for generic review action (APPROVE or REJECT)."""

    action: str = Field(..., description="Action to take: 'APPROVE' or 'REJECT'")
    reviewer_id: str = Field(
        ..., min_length=1, max_length=128,
        description="Municipal reviewer identifier",
    )
    notes: str | None = Field(
        None, max_length=512, description="Optional reviewer notes / reason",
    )
    link_to_issue_id: uuid.UUID | None = Field(
        None, description="Optional alternative issue ID when rejecting",
    )


class ReviewActionResponse(BaseModel):
    """Response after approve or reject action."""

    match_id: uuid.UUID
    status: str
    report_id: uuid.UUID
    issue_id: uuid.UUID | None = None
    reviewer_id: str
    reviewed_at: datetime.datetime | None = None

    @field_validator("reviewed_at", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        return ensure_utc(v)

    @field_serializer("reviewed_at", when_used="json-unless-none")
    def serialize_utc(self, v: datetime.datetime | None) -> str | None:
        if v is None:
            return None
        res = ensure_utc(v)
        assert res is not None
        return res.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)
