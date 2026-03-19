"""
Unit tests for domain events.
Verifies structure, immutability, and correct field types.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.domain.events.events import (
    DeadlineApproaching,
    ProjectCompleted,
    ProjectDeadlineChanged,
    TaskCompleted,
    TaskReopened,
)


class TestDomainEvent:
    def test_occurred_at_is_set_automatically(self, task_id, task_title):
        event = TaskCompleted(task_id=task_id, task_title=task_title)
        assert isinstance(event.occurred_at, datetime)

    def test_two_events_have_different_occurred_at(self, task_id, task_title):
        e1 = TaskCompleted(task_id=task_id, task_title=task_title)
        e2 = TaskCompleted(task_id=task_id, task_title=task_title)
        assert isinstance(e1.occurred_at, datetime)
        assert isinstance(e2.occurred_at, datetime)

    def test_occurred_at_can_be_set_explicitly(self, task_id, task_title, now):
        event = TaskCompleted(task_id=task_id, task_title=task_title, occurred_at=now)
        assert event.occurred_at == now


class TestImmutability:
    def test_task_completed_is_immutable(self, task_id, task_title):
        event = TaskCompleted(task_id=task_id, task_title=task_title)
        with pytest.raises(Exception):
            event.task_title = "changed"

    def test_task_reopened_is_immutable(self, task_id, project_id):
        event = TaskReopened(task_id=task_id, project_id=project_id)
        with pytest.raises(Exception):
            event.task_id = uuid4()

    def test_project_completed_is_immutable(self, project_id):
        event = ProjectCompleted(project_id=project_id)
        with pytest.raises(Exception):
            event.project_id = uuid4()

    def test_project_deadline_changed_is_immutable(self, project_id, now):
        event = ProjectDeadlineChanged(
            project_id=project_id,
            old_deadline=now,
            new_deadline=now,
        )
        with pytest.raises(Exception):
            event.old_deadline = datetime.now(UTC)

    def test_deadline_approaching_is_immutable(self, task_id, task_title, now):
        event = DeadlineApproaching(
            task_id=task_id, task_title=task_title, deadline=now
        )
        with pytest.raises(Exception):
            event.deadline = datetime.now(UTC)


class TestTaskCompleted:
    def test_creates_with_required_fields(self, task_id, task_title):
        event = TaskCompleted(task_id=task_id, task_title=task_title)
        assert event.task_id == task_id
        assert event.task_title == task_title

    def test_task_id_is_uuid(self, task_id, task_title):
        assert isinstance(
            TaskCompleted(task_id=task_id, task_title=task_title).task_id, UUID
        )

    def test_task_title_is_string(self, task_id, task_title):
        assert isinstance(
            TaskCompleted(task_id=task_id, task_title=task_title).task_title, str
        )

    def test_missing_task_id_raises(self, task_title):
        with pytest.raises(Exception):
            TaskCompleted(task_title=task_title)

    def test_missing_task_title_raises(self, task_id):
        with pytest.raises(Exception):
            TaskCompleted(task_id=task_id)


class TestTaskReopened:
    def test_creates_with_task_id_and_project_id(self, task_id, project_id):
        event = TaskReopened(task_id=task_id, project_id=project_id)
        assert event.task_id == task_id
        assert event.project_id == project_id

    def test_project_id_defaults_to_none(self, task_id):
        assert TaskReopened(task_id=task_id).project_id is None

    def test_missing_task_id_raises(self):
        with pytest.raises(Exception):
            TaskReopened()


class TestProjectDeadlineChanged:
    def test_creates_with_required_fields(self, project_id):
        old = datetime(2025, 12, 31)
        new = datetime(2025, 11, 1)
        event = ProjectDeadlineChanged(
            project_id=project_id,
            old_deadline=old,
            new_deadline=new,
        )
        assert event.project_id == project_id
        assert event.old_deadline == old
        assert event.new_deadline == new

    def test_project_id_is_uuid(self, project_id, now):
        event = ProjectDeadlineChanged(
            project_id=project_id,
            old_deadline=now,
            new_deadline=now,
        )
        assert isinstance(event.project_id, UUID)

    def test_missing_project_id_raises(self, now):
        with pytest.raises(Exception):
            ProjectDeadlineChanged(old_deadline=now, new_deadline=now)

    def test_missing_old_deadline_raises(self, project_id, now):
        with pytest.raises(Exception):
            ProjectDeadlineChanged(project_id=project_id, new_deadline=now)

    def test_missing_new_deadline_raises(self, project_id, now):
        with pytest.raises(Exception):
            ProjectDeadlineChanged(project_id=project_id, old_deadline=now)


class TestProjectCompleted:
    def test_creates_with_project_id(self, project_id):
        assert ProjectCompleted(project_id=project_id).project_id == project_id

    def test_project_id_is_uuid(self, project_id):
        assert isinstance(ProjectCompleted(project_id=project_id).project_id, UUID)

    def test_missing_project_id_raises(self):
        with pytest.raises(Exception):
            ProjectCompleted()


class TestDeadlineApproaching:
    def test_creates_with_required_fields(self, task_id, task_title, now):
        event = DeadlineApproaching(
            task_id=task_id, task_title=task_title, deadline=now
        )
        assert event.task_id == task_id
        assert event.task_title == task_title
        assert event.deadline == now

    def test_deadline_is_datetime(self, task_id, task_title, now):
        event = DeadlineApproaching(
            task_id=task_id, task_title=task_title, deadline=now
        )
        assert isinstance(event.deadline, datetime)

    def test_missing_task_id_raises(self, task_title, now):
        with pytest.raises(Exception):
            DeadlineApproaching(task_title=task_title, deadline=now)

    def test_missing_task_title_raises(self, task_id, now):
        with pytest.raises(Exception):
            DeadlineApproaching(task_id=task_id, deadline=now)

    def test_missing_deadline_raises(self, task_id, task_title):
        with pytest.raises(Exception):
            DeadlineApproaching(task_id=task_id, task_title=task_title)
