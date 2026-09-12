import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ai_analysis import AIAnalysis


class ModelVersion(Base):
    """Tracks provenance and versioning of ML models and preprocessing pipelines."""

    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    preprocessing_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    # Relationships
    ai_analyses: Mapped[list["AIAnalysis"]] = relationship(
        "AIAnalysis", back_populates="model_version"
    )
