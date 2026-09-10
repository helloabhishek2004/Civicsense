from abc import ABC, abstractmethod
from typing import Any


class ITextService(ABC):
    """Abstract interface for text analytics, tokenization, and contextual extraction."""

    @abstractmethod
    def analyze_text(self, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform text classification and safety context extraction.

        Raises:
            NotImplementedError: Text analytics is deferred to Sprint 4.
        """
        raise NotImplementedError(
            "Text analytics service is not implemented in the Phase 0 bootstrap foundation."
        )

    @abstractmethod
    def extract_embeddings(self, text: str) -> list[float]:
        """Generate semantic text representation vector.

        Raises:
            NotImplementedError: Text embeddings are deferred to Sprint 4.
        """
        raise NotImplementedError(
            "Text embedding service is not implemented in the Phase 0 bootstrap foundation."
        )
