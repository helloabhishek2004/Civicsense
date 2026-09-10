from abc import ABC, abstractmethod
from typing import Any


class IFusionService(ABC):
    """Abstract interface for multimodal fusion across visual, textual, and spatial signals."""

    @abstractmethod
    def fuse(
        self,
        image_features: list[float],
        text_features: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Combine multimodal representations and detect cross-modal agreement/conflict.

        Raises:
            NotImplementedError: Multimodal fusion is deferred to Sprint 5.
        """
        raise NotImplementedError(
            "Multimodal fusion service is not implemented in the Phase 0 bootstrap foundation."
        )
