import logging

from src.domain.events.events import (
    DeadlineApproaching,
    DomainEvent,
    ProjectCompleted,
    ProjectDeadlineChanged,
    TaskCompleted,
    TaskReopened,
)
from src.domain.ports.notification import NotificationPort

logger = logging.getLogger(__name__)


class ConsoleNotificationService(NotificationPort):
    """
    Driven adapter — reacts to domain events by logging to console.
    """

    def notify(self, event: DomainEvent) -> None:
        if isinstance(event, TaskCompleted):
            self._on_task_completed(event)

        elif isinstance(event, TaskReopened):
            self._on_task_reopened(event)

        elif isinstance(event, ProjectCompleted):
            self._on_project_completed(event)

        elif isinstance(event, ProjectDeadlineChanged):
            self._on_project_deadline_changed(event)

        elif isinstance(event, DeadlineApproaching):
            self._on_deadline_approaching(event)

        else:
            logger.debug(
                "Unhandled domain event: %s",
                type(event).__name__,
            )

    def _on_task_completed(self, event: TaskCompleted) -> None:
        logger.info(
            "Task completed — id=%s title=%r",
            event.task_id,
            event.task_title,
        )

    def _on_task_reopened(self, event: TaskReopened) -> None:
        logger.info(
            "Task reopened — id=%s project_id=%s",
            event.task_id,
            event.project_id,
        )

    def _on_project_completed(self, event: ProjectCompleted) -> None:
        logger.info(
            "Project completed — id=%s",
            event.project_id,
        )

    def _on_project_deadline_changed(self, event: ProjectDeadlineChanged) -> None:
        logger.warning(
            "Project deadline changed — id=%s old=%s new=%s",
            event.project_id,
            event.old_deadline.isoformat(),
            event.new_deadline.isoformat(),
        )

    def _on_deadline_approaching(self, event: DeadlineApproaching) -> None:
        logger.warning(
            "Deadline approaching within 24h — id=%s title=%r deadline=%s",
            event.task_id,
            event.task_title,
            event.deadline.isoformat(),
        )
