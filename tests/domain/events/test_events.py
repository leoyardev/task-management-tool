"""
Unit tests for domain events.

Verifies structure, immutability, and correct field types.
No database, no framework — pure domain logic only.
"""
import pytest
from datetime import datetime, UTC
from uuid import UUID, uuid4

from src.domain.events.events import (
    TaskCompleted,
    TaskReopened,
    ProjectDeadlineChanged,
    ProjectCompleted,
    DeadlineApproaching,
)



TASK_ID = uuid4()
PROJECT_ID = uuid4()
TASK_TITLE = "Write unit tests"
NOW = datetime.now(UTC)



class TestDomainEvent:

    def test_occurred_at_is_set_automatically(self):
        event = TaskCompleted(task_id=TASK_ID, task_title=TASK_TITLE)
        assert isinstance(event.occurred_at, datetime)

    def test_two_events_have_different_occurred_at(self):
        e1 = TaskCompleted(task_id=TASK_ID, task_title=TASK_TITLE)
        e2 = TaskCompleted(task_id=TASK_ID, task_title=TASK_TITLE)
        # both are valid datetimes — not the same frozen timestamp
        assert isinstance(e1.occurred_at, datetime)
        assert isinstance(e2.occurred_at, datetime)

    def test_occurred_at_can_be_set_explicitly(self):
        event = TaskCompleted(
            task_id=TASK_ID,
            task_title=TASK_TITLE,
            occurred_at=NOW,
        )
        assert event.occurred_at == NOW



class TestImmutability:

    def test_task_completed_is_immutable(self):
        event = TaskCompleted(task_id=TASK_ID, task_title=TASK_TITLE)
        with pytest.raises(Exception):
            event.task_title = "changed"

    def test_task_reopened_is_immutable(self):
        event = TaskReopened(task_id=TASK_ID, project_id=PROJECT_ID)
        with pytest.raises(Exception):
            event.task_id = uuid4()

    def test_project_completed_is_immutable(self):
        event = ProjectCompleted(project_id=PROJECT_ID)
        with pytest.raises(Exception):
            event.project_id = uuid4()

    def test_project_deadline_changed_is_immutable(self):
        event = ProjectDeadlineChanged(
            project_id=PROJECT_ID,
            old_deadline=NOW,
            new_deadline=NOW,
        )
        with pytest.raises(Exception):
            event.old_deadline = datetime.now(UTC)

    def test_deadline_approaching_is_immutable(self):
        event = DeadlineApproaching(
            task_id=TASK_ID,
            task_title=TASK_TITLE,
            deadline=NOW,
        )
        with pytest.raises(Exception):
            event.deadline = datetime.now(UTC)



class TestTaskCompleted:

    def test_creates_with_required_fields(self):
        event = TaskCompleted(task_id=TASK_ID, task_title=TASK_TITLE)
        assert event.task_id == TASK_ID
        assert event.task_title == TASK_TITLE

    def test_task_id_is_uuid(self):
        event = TaskCompleted(task_id=TASK_ID, task_title=TASK_TITLE)
        assert isinstance(event.task_id, UUID)

    def test_task_title_is_string(self):
        event = TaskCompleted(task_id=TASK_ID, task_title=TASK_TITLE)
        assert isinstance(event.task_title, str)

    def test_missing_task_id_raises(self):
        with pytest.raises(Exception):
            TaskCompleted(task_title=TASK_TITLE)

    def test_missing_task_title_raises(self):
        with pytest.raises(Exception):
            TaskCompleted(task_id=TASK_ID)



class TestTaskReopened:

    def test_creates_with_task_id_and_project_id(self):
        event = TaskReopened(task_id=TASK_ID, project_id=PROJECT_ID)
        assert event.task_id == TASK_ID
        assert event.project_id == PROJECT_ID

    def test_project_id_is_optional(self):
        event = TaskReopened(task_id=TASK_ID)
        assert event.project_id is None

    def test_project_id_defaults_to_none(self):
        event = TaskReopened(task_id=TASK_ID)
        assert event.project_id is None

    def test_missing_task_id_raises(self):
        with pytest.raises(Exception):
            TaskReopened()



class TestProjectDeadlineChanged:

    def test_creates_with_required_fields(self):
        old = datetime(2025, 12, 31)
        new = datetime(2025, 11, 1)
        event = ProjectDeadlineChanged(
            project_id=PROJECT_ID,
            old_deadline=old,
            new_deadline=new,
        )
        assert event.project_id == PROJECT_ID
        assert event.old_deadline == old
        assert event.new_deadline == new

    def test_project_id_is_uuid(self):
        event = ProjectDeadlineChanged(
            project_id=PROJECT_ID,
            old_deadline=NOW,
            new_deadline=NOW,
        )
        assert isinstance(event.project_id, UUID)

    def test_missing_project_id_raises(self):
        with pytest.raises(Exception):
            ProjectDeadlineChanged(old_deadline=NOW, new_deadline=NOW)

    def test_missing_old_deadline_raises(self):
        with pytest.raises(Exception):
            ProjectDeadlineChanged(project_id=PROJECT_ID, new_deadline=NOW)

    def test_missing_new_deadline_raises(self):
        with pytest.raises(Exception):
            ProjectDeadlineChanged(project_id=PROJECT_ID, old_deadline=NOW)



class TestProjectCompleted:

    def test_creates_with_project_id(self):
        event = ProjectCompleted(project_id=PROJECT_ID)
        assert event.project_id == PROJECT_ID

    def test_project_id_is_uuid(self):
        event = ProjectCompleted(project_id=PROJECT_ID)
        assert isinstance(event.project_id, UUID)

    def test_missing_project_id_raises(self):
        with pytest.raises(Exception):
            ProjectCompleted()



class TestDeadlineApproaching:

    def test_creates_with_required_fields(self):
        event = DeadlineApproaching(
            task_id=TASK_ID,
            task_title=TASK_TITLE,
            deadline=NOW,
        )
        assert event.task_id == TASK_ID
        assert event.task_title == TASK_TITLE
        assert event.deadline == NOW

    def test_deadline_is_datetime(self):
        event = DeadlineApproaching(
            task_id=TASK_ID,
            task_title=TASK_TITLE,
            deadline=NOW,
        )
        assert isinstance(event.deadline, datetime)

    def test_missing_task_id_raises(self):
        with pytest.raises(Exception):
            DeadlineApproaching(task_title=TASK_TITLE, deadline=NOW)

    def test_missing_task_title_raises(self):
        with pytest.raises(Exception):
            DeadlineApproaching(task_id=TASK_ID, deadline=NOW)

    def test_missing_deadline_raises(self):
        with pytest.raises(Exception):
            DeadlineApproaching(task_id=TASK_ID, task_title=TASK_TITLE)