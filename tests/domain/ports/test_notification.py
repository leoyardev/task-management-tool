"""
Unit tests for NotificationPort contract.
"""

from uuid import uuid4

import pytest

from src.domain.events.events import TaskCompleted
from src.domain.ports.notification import NotificationPort


class TestNotificationPort:
    def test_cannot_instantiate_without_implementation(self):
        with pytest.raises(TypeError):
            NotificationPort()

    def test_concrete_class_missing_notify_raises(self):
        class IncompleteNotifier(NotificationPort):
            pass  # notify() missing

        with pytest.raises(TypeError):
            IncompleteNotifier()

    def test_concrete_class_with_notify_can_instantiate(self):
        class FullNotifier(NotificationPort):
            def notify(self, event):
                pass

        assert FullNotifier() is not None

    def test_notify_receives_domain_event(self):
        received = []

        class SpyNotifier(NotificationPort):
            def notify(self, event):
                received.append(event)

        event = TaskCompleted(task_id=uuid4(), task_title="Deploy app")
        SpyNotifier().notify(event)
        assert len(received) == 1
        assert received[0] == event
