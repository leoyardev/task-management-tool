from abc import ABC, abstractmethod
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID

from src.domain.entities.task import Task



class TaskSpecification(ABC):
    """
    Base specification. Defines a business rule that can be checked
    against a Task instance and composed with other specifications.
    """

    @abstractmethod
    def is_satisfied_by(self, task: Task) -> bool: ...

    def __and__(self, other: "TaskSpecification") -> "AndSpecification":
        return AndSpecification(self, other)

    def __or__(self, other: "TaskSpecification") -> "OrSpecification":
        return OrSpecification(self, other)

    def __invert__(self) -> "NotSpecification":
        return NotSpecification(self)



class AndSpecification(TaskSpecification):
    def __init__(self, left: TaskSpecification, right: TaskSpecification) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, task: Task) -> bool:
        return self._left.is_satisfied_by(task) and self._right.is_satisfied_by(task)


class OrSpecification(TaskSpecification):
    def __init__(self, left: TaskSpecification, right: TaskSpecification) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, task: Task) -> bool:
        return self._left.is_satisfied_by(task) or self._right.is_satisfied_by(task)


class NotSpecification(TaskSpecification):
    def __init__(self, spec: TaskSpecification) -> None:
        self._spec = spec

    def is_satisfied_by(self, task: Task) -> bool:
        return not self._spec.is_satisfied_by(task)



class CompletedTaskSpec(TaskSpecification):
    """Matches tasks that are completed."""

    def is_satisfied_by(self, task: Task) -> bool:
        return task.completed is True


class OpenTaskSpec(TaskSpecification):
    """Matches tasks that are not completed."""

    def is_satisfied_by(self, task: Task) -> bool:
        return task.completed is False


class OverdueTaskSpec(TaskSpecification):
    """Matches tasks whose deadline has passed and are not completed."""

    def is_satisfied_by(self, task: Task) -> bool:
        return task.deadline < datetime.now(UTC) and not task.completed


class BelongsToProjectSpec(TaskSpecification):
    """Matches tasks belonging to a specific project."""

    def __init__(self, project_id: UUID) -> None:
        self._project_id = project_id

    def is_satisfied_by(self, task: Task) -> bool:
        return task.project_id == self._project_id


class UnlinkedTaskSpec(TaskSpecification):
    """Matches tasks not linked to any project."""

    def is_satisfied_by(self, task: Task) -> bool:
        return task.project_id is None



class TaskRepository(ABC):
    """
    Port — defines what any task persistence implementation must provide.

    The domain and application layers depend only on this interface.
    The actual implementation lives in adapters/persistence/ and is
    injected at startup via dependency injection.

    Usage examples:
        repo.find_all(CompletedTaskSpec())
        repo.find_all(BelongsToProjectSpec(project_id))
        repo.find_all(OverdueTaskSpec() & BelongsToProjectSpec(project_id))
        repo.find_all(OpenTaskSpec() | UnlinkedTaskSpec())
        repo.find_all(~CompletedTaskSpec())
    """

    @abstractmethod
    def save(self, task: Task) -> Task:
        """Insert or update a task. Returns the saved task."""
        pass

    @abstractmethod
    def find_by_id(self, task_id: UUID) -> Optional[Task]:
        """Return a task by id, or None if not found."""
        pass

    @abstractmethod
    def find_all(self, spec: Optional[TaskSpecification] = None) -> list[Task]:
        """
        Return all tasks, optionally filtered by a specification.
        Implementations must apply is_satisfied_by() per task
        or translate the spec to an equivalent query.
        """
        pass

    @abstractmethod
    def count_open_by_project(self, project_id: UUID) -> int:
        """
        Return the number of incomplete tasks for a project.
        Used by ProjectService to enforce the completion rule.
        Kept as explicit method — called frequently, benefits
        from a direct COUNT query over loading all tasks.
        """
        pass

    @abstractmethod
    def find_exceeding_deadline(
        self,
        project_id: UUID,
        deadline: datetime,
    ) -> list[Task]:
        """
        Return tasks in a project whose deadline exceeds the given datetime.
        Called when a project deadline is tightened to find tasks
        that now violate the constraint.
        """
        pass

    @abstractmethod
    def delete(self, task_id: UUID) -> None:
        """Delete a task by id."""
        pass