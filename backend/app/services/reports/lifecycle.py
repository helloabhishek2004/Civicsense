from app.core.errors import InvalidStateTransitionError
from app.models.enums import ReportStatus


class ReportLifecycleManager:
    """Explicit domain-level state machine governing valid report lifecycle transitions.

    States:
      SUBMITTED -> AI_PROCESSING -> AI_PROCESSED -> VERIFICATION_REQUIRED
      -> VERIFIED -> PRIORITIZED -> ASSIGNED -> IN_PROGRESS -> RESOLVED
      -> RESOLUTION_VERIFIED -> CLOSED
    """

    # Mapping from current state to the set of allowed destination states
    _TRANSITION_MAP: dict[ReportStatus, set[ReportStatus]] = {
        ReportStatus.SUBMITTED: {
            ReportStatus.AI_PROCESSING,
            ReportStatus.CLOSED,  # e.g., immediate spam/abuse discard
        },
        ReportStatus.AI_PROCESSING: {
            ReportStatus.AI_PROCESSED,
            ReportStatus.VERIFICATION_REQUIRED,
        },
        ReportStatus.AI_PROCESSED: {
            ReportStatus.VERIFICATION_REQUIRED,
            ReportStatus.VERIFIED,
            ReportStatus.PRIORITIZED,
        },
        ReportStatus.VERIFICATION_REQUIRED: {
            ReportStatus.VERIFIED,
            ReportStatus.CLOSED,  # Reviewer rejects report
        },
        ReportStatus.VERIFIED: {
            ReportStatus.PRIORITIZED,
            ReportStatus.CLOSED,
        },
        ReportStatus.PRIORITIZED: {
            ReportStatus.ASSIGNED,
            ReportStatus.IN_PROGRESS,
        },
        ReportStatus.ASSIGNED: {
            ReportStatus.IN_PROGRESS,
            ReportStatus.PRIORITIZED,
        },
        ReportStatus.IN_PROGRESS: {
            ReportStatus.RESOLVED,
            ReportStatus.ASSIGNED,
        },
        ReportStatus.RESOLVED: {
            ReportStatus.RESOLUTION_VERIFIED,
            ReportStatus.IN_PROGRESS,  # If work was inadequate
        },
        ReportStatus.RESOLUTION_VERIFIED: {
            ReportStatus.CLOSED,
        },
        ReportStatus.CLOSED: set(),  # Terminal state
    }

    @classmethod
    def get_allowed_transitions(cls, current_state: ReportStatus) -> set[ReportStatus]:
        """Return the set of valid states that can follow the given current state."""
        return cls._TRANSITION_MAP.get(current_state, set())

    @classmethod
    def is_valid_transition(cls, current_state: ReportStatus, next_state: ReportStatus) -> bool:
        """Check whether moving from current_state to next_state is permitted."""
        return next_state in cls.get_allowed_transitions(current_state)

    @classmethod
    def validate_transition(cls, current_state: ReportStatus, next_state: ReportStatus) -> None:
        """Validate a transition; raises InvalidStateTransitionError if illegal."""
        if current_state == next_state:
            return

        if not cls.is_valid_transition(current_state, next_state):
            allowed = [s.value for s in cls.get_allowed_transitions(current_state)]
            allowed_msg = (
                f"Allowed next states: {', '.join(allowed) if allowed else 'None (Terminal state)'}"
            )
            raise InvalidStateTransitionError(
                from_state=current_state.value,
                to_state=next_state.value,
                reason=allowed_msg,
            )
