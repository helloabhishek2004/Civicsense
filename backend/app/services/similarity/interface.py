from abc import ABC, abstractmethod
from typing import Any


class ISimilarityService(ABC):
    """Abstract interface for duplicate detection and nearest neighbor similarity queries."""

    @abstractmethod
    def find_similar_reports(
        self,
        latitude: float,
        longitude: float,
        embedding: list[float] | None = None,
        radius_meters: float = 100.0,
    ) -> list[dict[str, Any]]:
        """Identify potentially related or duplicate reports based on multimodal + spatial
        proximity.

        Raises:
            NotImplementedError: Similarity and duplicate detection are deferred to Sprint 5.
        """
        raise NotImplementedError(
            "Similarity and duplicate detection service is not implemented in "
            "the Phase 0 bootstrap foundation."
        )
