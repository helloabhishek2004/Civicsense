import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class MetricItem(BaseModel, Generic[T]):
    """Individual metric container supporting insufficient data handling."""

    value: T | None = None
    sample_size: int = 0
    display_state: str = "AVAILABLE"  # AVAILABLE or INSUFFICIENT_DATA


class AIMetricsResponse(BaseModel):
    """Real database-derived operational AI metrics."""

    total_jobs: MetricItem[int]
    completed_jobs: MetricItem[int]
    failed_jobs: MetricItem[int]
    active_jobs: MetricItem[int]
    awaiting_human_review: MetricItem[int]
    avg_processing_latency_ms: MetricItem[float]
    low_confidence_rate: MetricItem[float]
    modality_disagreement_rate: MetricItem[float]
    human_override_rate: MetricItem[float]
    time_window: str = "ALL_TIME"
    generated_at: datetime.datetime
