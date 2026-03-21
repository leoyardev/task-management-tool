"""
Unit tests for domain exceptions.

Verifies exception hierarchy, messages, and attributes.
"""

import pytest

from src.domain.exceptions.exceptions import (
    DeadlineViolationError,
    DomainException,
    InvalidOperationError,
    NotFoundError,
    ProjectCompletionError,
    TaskAlreadyCompletedError,
)


class TestDomainException:
    def test_is_base_exception(self):
        exc = DomainException("something went wrong")
        assert isinstance(exc, Exception)

    def test_all_exceptions_inherit_from_domain_exception(self):
        assert issubclass(NotFoundError, DomainException)
        assert issubclass(DeadlineViolationError, DomainException)
        assert issubclass(ProjectCompletionError, DomainException)
        assert issubclass(TaskAlreadyCompletedError, DomainException)
        assert issubclass(InvalidOperationError, DomainException)

    def test_can_be_caught_as_base(self):
        with pytest.raises(DomainException):
            raise NotFoundError("Task", "123")


class TestNotFoundError:
    def test_message_includes_entity_and_id(self):
        exc = NotFoundError("Task", "abc-123")
        assert "Task" in str(exc)
        assert "abc-123" in str(exc)

    def test_entity_attribute(self):
        exc = NotFoundError("Project", "xyz-456")
        assert exc.entity == "Project"

    def test_entity_id_attribute(self):
        exc = NotFoundError("Project", "xyz-456")
        assert exc.entity_id == "xyz-456"

    def test_is_raised_correctly(self):
        with pytest.raises(NotFoundError):
            raise NotFoundError("Task", "abc-123")

    def test_can_be_caught_as_domain_exception(self):
        with pytest.raises(DomainException):
            raise NotFoundError("Task", "abc-123")


class TestDeadlineViolationError:
    def test_is_raised_with_message(self):
        with pytest.raises(DeadlineViolationError, match="exceeds"):
            raise DeadlineViolationError("Task deadline exceeds project deadline.")

    def test_can_be_caught_as_domain_exception(self):
        with pytest.raises(DomainException):
            raise DeadlineViolationError("Task deadline exceeds project deadline.")

    def test_message_is_preserved(self):
        msg = "Task deadline '2025-12-31' exceeds project deadline '2025-11-01'."
        exc = DeadlineViolationError(msg)
        assert str(exc) == msg


class TestProjectCompletionError:
    def test_is_raised_with_message(self):
        with pytest.raises(ProjectCompletionError, match="open"):
            raise ProjectCompletionError(
                "Cannot complete project: 3 task(s) still open."
            )

    def test_can_be_caught_as_domain_exception(self):
        with pytest.raises(DomainException):
            raise ProjectCompletionError("Cannot complete project.")

    def test_message_is_preserved(self):
        msg = "Cannot complete project 'Launch': 2 task(s) still open."
        exc = ProjectCompletionError(msg)
        assert str(exc) == msg


class TestTaskAlreadyCompletedError:
    def test_is_raised_with_message(self):
        with pytest.raises(TaskAlreadyCompletedError):
            raise TaskAlreadyCompletedError("Task 'Write tests' is already completed.")

    def test_can_be_caught_as_domain_exception(self):
        with pytest.raises(DomainException):
            raise TaskAlreadyCompletedError("Task is already completed.")

    def test_message_is_preserved(self):
        msg = "Task 'Deploy app' is already completed."
        exc = TaskAlreadyCompletedError(msg)
        assert str(exc) == msg


class TestInvalidOperationError:
    def test_is_raised_with_message(self):
        with pytest.raises(InvalidOperationError):
            raise InvalidOperationError("Project is already completed.")

    def test_can_be_caught_as_domain_exception(self):
        with pytest.raises(DomainException):
            raise InvalidOperationError("Invalid operation.")

    def test_message_is_preserved(self):
        msg = "Project 'Launch' is already completed."
        exc = InvalidOperationError(msg)
        assert str(exc) == msg
