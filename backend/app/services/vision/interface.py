from abc import ABC, abstractmethod
from typing import Any


class IVisionService(ABC):
    """Abstract interface for machine vision models and image preprocessing pipelines."""

    @abstractmethod
    def analyze_image(
        self, image_uri: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Perform vision inference (detection, classification, feature extraction).

        Raises:
            NotImplementedError: Machine vision models are deferred to Sprint 3.
        """
        raise NotImplementedError(
            "Machine vision service is not implemented in the Phase 0 bootstrap foundation."
        )

    @abstractmethod
    def extract_embeddings(self, image_uri: str) -> list[float]:
        """Extract visual feature embeddings from an image.

        Raises:
            NotImplementedError: Vision embeddings are deferred to Sprint 3.
        """
        raise NotImplementedError(
            "Vision embedding extraction is not implemented in the Phase 0 bootstrap foundation."
        )
