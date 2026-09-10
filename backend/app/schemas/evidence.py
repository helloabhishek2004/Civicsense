import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EvidenceType


class EvidenceBase(BaseModel):
    """Base fields for evidence referencing."""

    evidence_type: EvidenceType
    storage_uri: str = Field(..., max_length=512)
    file_hash: str | None = Field(None, max_length=128)
    mime_type: str | None = Field(None, max_length=64)
    file_size_bytes: int | None = Field(None, ge=0)
    metadata_json: dict[str, Any] | None = None


class EvidenceCreate(EvidenceBase):
    """Payload for creating an evidence attachment."""

    pass


class EvidenceRead(EvidenceBase):
    """Schema for returning evidence details."""

    id: uuid.UUID
    report_id: uuid.UUID
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
