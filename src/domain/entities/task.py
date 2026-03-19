from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from src.domain.events.events import (
    DomainEvent,
    TaskCompleted,
    TaskReopened,
)
from src.domain.exceptions.exceptions import (
    DeadlineViolationError,
    InvalidOperationError,
    TaskAlreadyCompletedError,
)


@dataclass
class Task:
    """
    Task entity.

    Rules enforced here:
      - Task deadline must never exceed its project deadline
      - Cannot be marked complete if already completed
      - Deadline is rolled back if update violates project deadline
      - Linking to a project validates deadline immediately
    """

    id: UUID
    title: str
    deadline: datetime
    completed: bool = False
    description: Optional[str] = None
    project_id: Optional[UUID] = None
    project_deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _events: list[DomainEvent] = field(
        default_factory=list,
        repr=False,
        compare=False,
    )


    @staticmethod
    def create(
        title: str,
        deadline: datetime,
        description: Optional[str] = None,
        project_id: Optional[UUID] = None,
        project_deadline: Optional[datetime] = None,
    ) -> "Task":
        task = Task(
            id=uuid4(),
            title=title,
            deadline=deadline,
            description=description,
            project_id=project_id,
            project_deadline=project_deadline,
        )
        task._validate_deadline()
        return task


    def _validate_deadline(self) -> None:
        """
        A task deadline must never exceed its project deadline.
        Called on create, update, and link_to_project.
        """
        if self.project_deadline and self.deadline > self.project_deadline:
            raise DeadlineViolationError(
                f"Task deadline '{self.deadline}' exceeds "
                f"project deadline '{self.project_deadline}'."
            )

    def mark_complete(self) -> None:
        """
        Mark the task as completed.
        Raises TaskAlreadyCompletedError if already completed.
        """
        if self.completed:
            raise TaskAlreadyCompletedError(
                f"Task '{self.title}' is already completed."
            )
        self.completed = True
        self.updated_at = datetime.now(UTC)
        self._events.append(
            TaskCompleted(task_id=self.id, task_title=self.title)
        )

    def reopen(self) -> None:
        """
        Reopen a completed task.
        Emits TaskReopened with project_id so the application layer
        can reopen the parent project if it was completed.
        """
        self.completed = False
        self.updated_at = datetime.now(UTC)
        self._events.append(
            TaskReopened(task_id=self.id, project_id=self.project_id)
        )

    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        deadline: Optional[datetime] = None,
    ) -> None:
        """
        Update mutable fields.
        Raises InvalidOperationError if no fields are provided.
        Rolls back deadline if it violates the project deadline.
        """
        if title is None and description is None and deadline is None:
            raise InvalidOperationError("No fields provided to update.")

        if title is not None:
            self.title = title

        if description is not None:
            self.description = description

        if deadline is not None:
            previous_deadline = self.deadline
            self.deadline = deadline
            try:
                self._validate_deadline()
            except DeadlineViolationError:
                self.deadline = previous_deadline
                raise

        self.updated_at = datetime.now(UTC)

    def link_to_project(
        self,
        project_id: UUID,
        project_deadline: datetime,
    ) -> None:
        """
        Link this task to a project.
        Validates immediately that the task deadline does not
        exceed the project deadline.
        """
        self.project_id = project_id
        self.project_deadline = project_deadline
        self._validate_deadline()
        self.updated_at = datetime.now(UTC)

    def unlink_from_project(self) -> None:
        """
        Remove the task from its project.
        Clears project_id and project_deadline — task is now free
        standing with no deadline constraint.
        """
        self.project_id = None
        self.project_deadline = None
        self.updated_at = datetime.now(UTC)


    def pull_events(self) -> list[DomainEvent]:
        """
        Return all pending domain events and clear the internal list.
        Called by the application layer after every command.
        """
        events, self._events = self._events, []
        return events