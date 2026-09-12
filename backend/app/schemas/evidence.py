import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.enums import EvidenceType
from app.schemas.common import ensure_utc


class EvidenceBase(BaseModel):
    """Base fields for evidence referencing."""

    evidence_type: EvidenceType
    storage_uri: str = Field(default="pending", max_length=512)
    file_hash: str | None = Field(None, max_length=128)
    mime_type: str | None = Field(None, max_length=64)
    file_size_bytes: int | None = Field(None, ge=0)
    metadata_json: dict[str, Any] | None = None


class EvidenceCreate(EvidenceBase):
    """Payload for creating an evidence attachment."""

    data_base64: str | None = Field(
        None, description="Optional base64-encoded image data for edge upload"
    )


class EvidenceRead(EvidenceBase):
    """Schema for returning evidence details."""

    id: uuid.UUID
    report_id: uuid.UUID
    created_at: datetime.datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime.datetime) -> datetime.datetime:
        res = ensure_utc(v)
        assert res is not None
        return res

    @field_serializer("created_at", when_used="json-unless-none")
    def serialize_utc(self, v: datetime.datetime) -> str:
        res = ensure_utc(v)
        assert res is not None
        return res.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)
