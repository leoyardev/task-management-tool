"""
Unit tests for ConsoleNotificationService.

Verifies correct log level and message content for each domain event.
Uses pytest caplog to capture log output — no mocks needed.
"""

from datetime import timedelta

from src.domain.events.events import (
    DeadlineApproaching,
    DomainEvent,
    ProjectCompleted,
    ProjectDeadlineChanged,
    TaskCompleted,
    TaskReopened,
)
from src.domain.ports.notification import NotificationPort


class TestConsoleNotificationServiceContract:
    def test_implements_notification_port(self, notifier):
        assert isinstance(notifier, NotificationPort)


class TestTaskCompleted:
    def test_logs_at_info_level(self, notifier, caplog, task_id, task_title):
        event = TaskCompleted(task_id=task_id, task_title=task_title)
        with caplog.at_level("INFO"):
            notifier.notify(event)
        assert any(r.levelname == "INFO" for r in caplog.records)

    def test_log_contains_task_id(self, notifier, caplog, task_id, task_title):
        event = TaskCompleted(task_id=task_id, task_title=task_title)
        with caplog.at_level("INFO"):
            notifier.notify(event)
        assert str(task_id) in caplog.text

    def test_log_contains_task_title(self, notifier, caplog, task_id, task_title):
        event = TaskCompleted(task_id=task_id, task_title=task_title)
        with caplog.at_level("INFO"):
            notifier.notify(event)
        assert task_title in caplog.text


class TestTaskReopened:
    def test_logs_at_info_level(self, notifier, caplog, task_id, project_id):
        event = TaskReopened(task_id=task_id, project_id=project_id)
        with caplog.at_level("INFO"):
            notifier.notify(event)
        assert any(r.levelname == "INFO" for r in caplog.records)

    def test_log_contains_task_id(self, notifier, caplog, task_id, project_id):
        event = TaskReopened(task_id=task_id, project_id=project_id)
        with caplog.at_level("INFO"):
            notifier.notify(event)
        assert str(task_id) in caplog.text

    def test_log_contains_project_id(self, notifier, caplog, task_id, project_id):
        event = TaskReopened(task_id=task_id, project_id=project_id)
        with caplog.at_level("INFO"):
            notifier.notify(event)
        assert str(project_id) in caplog.text


class TestProjectCompleted:
    def test_logs_at_info_level(self, notifier, caplog, project_id):
        event = ProjectCompleted(project_id=project_id)
        with caplog.at_level("INFO"):
            notifier.notify(event)
        assert any(r.levelname == "INFO" for r in caplog.records)

    def test_log_contains_project_id(self, notifier, caplog, project_id):
        event = ProjectCompleted(project_id=project_id)
        with caplog.at_level("INFO"):
            notifier.notify(event)
        assert str(project_id) in caplog.text


class TestProjectDeadlineChanged:
    def test_logs_at_warning_level(self, notifier, caplog, project_id, now):
        event = ProjectDeadlineChanged(
            project_id=project_id,
            old_deadline=now + timedelta(days=10),
            new_deadline=now + timedelta(days=5),
        )
        with caplog.at_level("WARNING"):
            notifier.notify(event)
        assert any(r.levelname == "WARNING" for r in caplog.records)

    def test_log_contains_project_id(self, notifier, caplog, project_id, now):
        event = ProjectDeadlineChanged(
            project_id=project_id,
            old_deadline=now + timedelta(days=10),
            new_deadline=now + timedelta(days=5),
        )
        with caplog.at_level("WARNING"):
            notifier.notify(event)
        assert str(project_id) in caplog.text

    def test_log_contains_old_and_new_deadline(self, notifier, caplog, project_id, now):
        old = now + timedelta(days=10)
        new = now + timedelta(days=5)
        event = ProjectDeadlineChanged(
            project_id=project_id,
            old_deadline=old,
            new_deadline=new,
        )
        with caplog.at_level("WARNING"):
            notifier.notify(event)
        assert old.isoformat() in caplog.text
        assert new.isoformat() in caplog.text


class TestDeadlineApproaching:
    def test_logs_at_warning_level(self, notifier, caplog, task_id, task_title, now):
        event = DeadlineApproaching(
            task_id=task_id,
            task_title=task_title,
            deadline=now + timedelta(hours=12),
        )
        with caplog.at_level("WARNING"):
            notifier.notify(event)
        assert any(r.levelname == "WARNING" for r in caplog.records)

    def test_log_contains_task_id(self, notifier, caplog, task_id, task_title, now):
        event = DeadlineApproaching(
            task_id=task_id,
            task_title=task_title,
            deadline=now + timedelta(hours=12),
        )
        with caplog.at_level("WARNING"):
            notifier.notify(event)
        assert str(task_id) in caplog.text

    def test_log_contains_task_title(self, notifier, caplog, task_id, task_title, now):
        event = DeadlineApproaching(
            task_id=task_id,
            task_title=task_title,
            deadline=now + timedelta(hours=12),
        )
        with caplog.at_level("WARNING"):
            notifier.notify(event)
        assert task_title in caplog.text

    def test_log_contains_deadline(self, notifier, caplog, task_id, task_title, now):
        deadline = now + timedelta(hours=12)
        event = DeadlineApproaching(
            task_id=task_id,
            task_title=task_title,
            deadline=deadline,
        )
        with caplog.at_level("WARNING"):
            notifier.notify(event)
        assert deadline.isoformat() in caplog.text


class TestUnhandledEvent:
    def test_unhandled_event_logs_at_debug(self, notifier, caplog):

        class UnknownEvent(DomainEvent):
            pass

        with caplog.at_level("DEBUG"):
            notifier.notify(UnknownEvent())
        assert any(r.levelname == "DEBUG" for r in caplog.records)

    def test_unhandled_event_logs_event_name(self, notifier, caplog):
        class UnknownEvent(DomainEvent):
            pass

        with caplog.at_level("DEBUG"):
            notifier.notify(UnknownEvent())
        assert "UnknownEvent" in caplog.text
