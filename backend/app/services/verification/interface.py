import uuid
from abc import ABC, abstractmethod
from typing import Any


class IVerificationService(ABC):
    """Abstract interface for human verification routing and feedback recording."""

    @abstractmethod
    def route_to_verification_queue(self, report_id: uuid.UUID, reason: str) -> bool:
        """Enqueue an ambiguous or critical report for human inspection.

        Raises:
            NotImplementedError: Human verification queueing is deferred to Sprint 6.
        """
        raise NotImplementedError(
            "Verification routing service is not implemented in the Phase 0 bootstrap foundation."
        )

    @abstractmethod
    def submit_verification_verdict(
        self,
        report_id: uuid.UUID,
        reviewer_id: str,
        verdict: dict[str, Any],
    ) -> dict[str, Any]:
        """Record reviewer corrections as ground truth and feed into MLOps.

        Raises:
            NotImplementedError: Verification feedback loop is deferred to Sprint 6.
        """
        raise NotImplementedError(
            "Verification verdict processing is not implemented in "
            "the Phase 0 bootstrap foundation."
        )
