from abc import ABC, abstractmethod
from typing import Any


class IDecisionService(ABC):
    """Abstract interface for the decision engine evaluating severity, priority, and routing."""

    @abstractmethod
    def evaluate(
        self,
        predicted_category: str,
        confidence: float,
        evidence_agreement: float,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compute severity, priority ranking, and human verification necessity.

        Raises:
            NotImplementedError: Decision engine scoring is deferred to Sprint 5.
        """
        raise NotImplementedError(
            "Decision engine service is not implemented in the Phase 0 bootstrap foundation."
        )
