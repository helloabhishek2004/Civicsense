import pytest

from app.core.errors import InvalidStateTransitionError
from app.models.enums import ReportStatus
from app.services.reports.lifecycle import ReportLifecycleManager


def test_all_valid_transitions() -> None:
    """Verify that every documented legal transition passes validation."""
    valid_pairs = [
        (ReportStatus.SUBMITTED, ReportStatus.AI_PROCESSING),
        (ReportStatus.SUBMITTED, ReportStatus.CLOSED),
        (ReportStatus.AI_PROCESSING, ReportStatus.AI_PROCESSED),
        (ReportStatus.AI_PROCESSING, ReportStatus.VERIFICATION_REQUIRED),
        (ReportStatus.AI_PROCESSED, ReportStatus.VERIFICATION_REQUIRED),
        (ReportStatus.AI_PROCESSED, ReportStatus.VERIFIED),
        (ReportStatus.AI_PROCESSED, ReportStatus.PRIORITIZED),
        (ReportStatus.VERIFICATION_REQUIRED, ReportStatus.VERIFIED),
        (ReportStatus.VERIFICATION_REQUIRED, ReportStatus.CLOSED),
        (ReportStatus.VERIFIED, ReportStatus.PRIORITIZED),
        (ReportStatus.VERIFIED, ReportStatus.CLOSED),
        (ReportStatus.PRIORITIZED, ReportStatus.ASSIGNED),
        (ReportStatus.PRIORITIZED, ReportStatus.IN_PROGRESS),
        (ReportStatus.ASSIGNED, ReportStatus.IN_PROGRESS),
        (ReportStatus.ASSIGNED, ReportStatus.PRIORITIZED),
        (ReportStatus.IN_PROGRESS, ReportStatus.RESOLVED),
        (ReportStatus.IN_PROGRESS, ReportStatus.ASSIGNED),
        (ReportStatus.RESOLVED, ReportStatus.RESOLUTION_VERIFIED),
        (ReportStatus.RESOLVED, ReportStatus.IN_PROGRESS),
        (ReportStatus.RESOLUTION_VERIFIED, ReportStatus.CLOSED),
    ]

    for from_state, to_state in valid_pairs:
        assert ReportLifecycleManager.is_valid_transition(from_state, to_state) is True
        # Should not raise exception
        ReportLifecycleManager.validate_transition(from_state, to_state)


def test_invalid_transitions_raise_error() -> None:
    """Verify that illegal state skips raise InvalidStateTransitionError."""
    invalid_pairs = [
        (ReportStatus.SUBMITTED, ReportStatus.RESOLVED),
        (ReportStatus.SUBMITTED, ReportStatus.IN_PROGRESS),
        (ReportStatus.AI_PROCESSING, ReportStatus.CLOSED),
        (ReportStatus.AI_PROCESSED, ReportStatus.RESOLVED),
        (ReportStatus.ASSIGNED, ReportStatus.CLOSED),
        (ReportStatus.RESOLVED, ReportStatus.SUBMITTED),
    ]

    for from_state, to_state in invalid_pairs:
        assert ReportLifecycleManager.is_valid_transition(from_state, to_state) is False
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            ReportLifecycleManager.validate_transition(from_state, to_state)
        assert exc_info.value.code == "INVALID_STATE_TRANSITION"


def test_terminal_state_closed_behavior() -> None:
    """Verify CLOSED is terminal and cannot transition to any other state."""
    allowed = ReportLifecycleManager.get_allowed_transitions(ReportStatus.CLOSED)
    assert len(allowed) == 0

    for state in ReportStatus:
        if state != ReportStatus.CLOSED:
            assert ReportLifecycleManager.is_valid_transition(ReportStatus.CLOSED, state) is False
            with pytest.raises(InvalidStateTransitionError):
                ReportLifecycleManager.validate_transition(ReportStatus.CLOSED, state)


def test_idempotent_self_transition() -> None:
    """Transitioning from state A to state A should be accepted as a no-op."""
    for state in ReportStatus:
        ReportLifecycleManager.validate_transition(state, state)
