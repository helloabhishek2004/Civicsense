import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class ModelVersionRead(BaseModel):
    """Schema for model provenance details."""

    id: uuid.UUID
    model_name: str
    model_version: str
    preprocessing_version: str | None = None
    embedding_model: str | None = None
    embedding_version: str | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
