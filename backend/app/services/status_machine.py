from app.schemas import Status

# The explicit transition table the assignment requires —
# not a chain of if/elif. Adding a new rule later means
# adding one line here, nothing else.
ALLOWED_TRANSITIONS: dict[Status, set[Status]] = {
    Status.open: {Status.in_progress, Status.rejected},
    Status.in_progress: {Status.resolved, Status.rejected},
    Status.resolved: set(),
    Status.rejected: set(),
}


class InvalidTransitionError(Exception):
    """Raised when a status change isn't allowed from the current status."""

    def __init__(self, current: Status, attempted: Status):
        self.current = current
        self.attempted = attempted
        super().__init__(f"Cannot transition from '{current.value}' to '{attempted.value}'")


def validate_transition(current: Status, attempted: Status) -> None:
    if attempted not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(current, attempted)
