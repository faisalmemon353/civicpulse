import pytest

from app.schemas import Status
from app.services.status_machine import InvalidTransitionError, validate_transition


def test_open_to_in_progress_is_allowed():
    validate_transition(Status.open, Status.in_progress)  # should not raise


def test_open_to_rejected_is_allowed():
    validate_transition(Status.open, Status.rejected)


def test_in_progress_to_resolved_is_allowed():
    validate_transition(Status.in_progress, Status.resolved)


def test_open_to_resolved_is_rejected():
    with pytest.raises(InvalidTransitionError):
        validate_transition(Status.open, Status.resolved)


def test_resolved_is_terminal():
    with pytest.raises(InvalidTransitionError):
        validate_transition(Status.resolved, Status.open)
