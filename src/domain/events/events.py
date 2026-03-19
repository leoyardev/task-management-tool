from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """
    Base class for all domain events.
    Events are immutable facts.
    """

    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": True}


class TaskCompleted(DomainEvent):
    """
    Fired when a task is marked as completed.

    Triggers:
      - NotificationService logs a message
      - TaskService checks if project should auto-complete
    """

    task_id: UUID
    task_title: str


class TaskReopened(DomainEvent):
    """
    Fired when a completed task is reopened.

    Triggers:
      - If the task belongs to a completed project,
        the application layer reopens the project too
    """

    task_id: UUID
    project_id: UUID | None = None


class ProjectDeadlineChanged(DomainEvent):
    """
    Fired when a project deadline moves to an earlier date.

    Triggers:
      - Application layer finds all tasks whose deadline now
        exceeds the new project deadline and adjusts them
    """

    project_id: UUID
    old_deadline: datetime
    new_deadline: datetime


class ProjectCompleted(DomainEvent):
    """
    Fired when a project is marked as completed.

    Triggers:
      - NotificationService logs a message
    """

    project_id: UUID


class DeadlineApproaching(DomainEvent):
    """
    Fired by a background scheduler — not by an entity.
    Fired when a task deadline is within 24 hours and not completed.

    Triggers:
      - NotificationService logs a warning
    """

    task_id: UUID
    task_title: str
    deadline: datetime
