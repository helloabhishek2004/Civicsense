from abc import ABC, abstractmethod
from typing import Any


class IAnalyticsService(ABC):
    """Abstract interface for data mining, hotspot detection, and pattern discovery."""

    @abstractmethod
    def detect_hotspots(
        self,
        category: str | None = None,
        min_cluster_size: int = 5,
    ) -> list[dict[str, Any]]:
        """Perform spatial clustering on accumulated historical reports.

        Raises:
            NotImplementedError: Data mining and hotspot clustering are deferred to Sprint 7.
        """
        raise NotImplementedError(
            "Analytics and spatial clustering service is not implemented in "
            "the Phase 0 bootstrap foundation."
        )

    @abstractmethod
    def mine_frequent_patterns(
        self, min_support: float = 0.05, min_confidence: float = 0.6
    ) -> list[dict[str, Any]]:
        """Extract recurring civic problem combinations (e.g. {Pothole, Water Accumulation}).

        Raises:
            NotImplementedError: Frequent pattern mining is deferred to Sprint 7.
        """
        raise NotImplementedError(
            "Pattern mining service is not implemented in the Phase 0 bootstrap foundation."
        )
