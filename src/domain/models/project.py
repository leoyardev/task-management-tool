
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from src.domain.events.events import (
    DomainEvent,
    ProjectCompleted,
    ProjectDeadlineChanged,
)
from src.domain.exceptions.exceptions import (
    InvalidOperationError,
    ProjectCompletionError,
)


@dataclass
class Project:
    """
    Core project entity.

    Rules enforced here:
      - Cannot be marked complete if any tasks are still open
      - Emits ProjectDeadlineChanged only when deadline moves earlier
      - Reopening is triggered by the application layer
        when a task inside this project is reopened
    """

    id: UUID
    title: str
    deadline: datetime
    completed: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _events: list[DomainEvent] = field(
        default_factory=list,
        repr=False,
        compare=False,
    )

    @staticmethod
    def create(title: str, deadline: datetime) -> "Project":
        return Project(
            id=uuid4(),
            title=title,
            deadline=deadline,
        )

    def mark_complete(self, open_task_count: int) -> None:
        """
        Mark the project as completed.

        Raises InvalidOperationError if already completed.
        Raises ProjectCompletionError if any tasks are still open.

        open_task_count is passed in by the application layer
        """
        if self.completed:
            raise InvalidOperationError(
                f"Project '{self.title}' is already completed."
            )
        if open_task_count > 0:
            raise ProjectCompletionError(
                f"Cannot complete project '{self.title}': "
                f"{open_task_count} task(s) still open."
            )
        self.completed = True
        self.updated_at = datetime.now(UTC)
        self._events.append(ProjectCompleted(project_id=self.id))

    def reopen(self) -> None:
        """
        Reopen a completed project.

        Called by the application layer when any task inside
        this project is reopened.
        """
        self.completed = False
        self.updated_at = datetime.now(UTC)

    def update(
        self,
        title: Optional[str] = None,
        deadline: Optional[datetime] = None,
    ) -> None:
        """
        Update mutable fields.
        """

        if title is None and deadline is None:
            raise InvalidOperationError("No fields provided to update.")
        
        if title is not None:
            self.title = title

        if deadline is not None:
            old_deadline = self.deadline
            self.deadline = deadline
            self.updated_at = datetime.now(UTC)
            if deadline < old_deadline:
                self._events.append(
                    ProjectDeadlineChanged(
                        project_id=self.id,
                        old_deadline=old_deadline,
                        new_deadline=deadline,
                    )
                )


    def pull_events(self) -> list[DomainEvent]:
        """
        Return all pending domain events and clear the internal list.
        Called by the application layer after every command.
        """
        events, self._events = self._events, []
        return events