"""
Unit tests for the Task domain entity.
"""
import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from src.domain.entities.task import Task
from src.domain.events.events import TaskCompleted, TaskReopened
from src.domain.exceptions.exceptions import (
    DeadlineViolationError,
    InvalidOperationError,
    TaskAlreadyCompletedError,
)


PROJECT_ID = uuid4()
PROJECT_DEADLINE = datetime(2025, 12, 31)


def make_task(**kwargs) -> Task:
    defaults = dict(
        title="Test task",
        deadline=datetime(2025, 11, 1),
    )
    return Task.create(**{**defaults, **kwargs})


def make_linked_task(**kwargs) -> Task:
    defaults = dict(
        title="Linked task",
        deadline=datetime(2025, 11, 1),
        project_id=PROJECT_ID,
        project_deadline=PROJECT_DEADLINE,
    )
    return Task.create(**{**defaults, **kwargs})



class TestTaskCreate:

    def test_creates_with_required_fields(self):
        task = make_task(title="Deploy", deadline=datetime(2025, 10, 1))
        assert task.title == "Deploy"
        assert task.deadline == datetime(2025, 10, 1)

    def test_id_is_auto_generated(self):
        task = make_task()
        assert isinstance(task.id, UUID)

    def test_two_tasks_have_unique_ids(self):
        assert make_task().id != make_task().id

    def test_completed_defaults_to_false(self):
        assert make_task().completed is False

    def test_description_defaults_to_none(self):
        assert make_task().description is None

    def test_project_id_defaults_to_none(self):
        assert make_task().project_id is None

    def test_project_deadline_defaults_to_none(self):
        assert make_task().project_deadline is None

    def test_created_at_is_set(self):
        assert make_task().created_at is not None

    def test_updated_at_is_set(self):
        assert make_task().updated_at is not None

    def test_events_list_is_empty_on_creation(self):
        assert make_task().pull_events() == []

    def test_creates_with_description(self):
        task = make_task(description="Some details")
        assert task.description == "Some details"

    def test_creates_with_project_linked(self):
        task = make_linked_task()
        assert task.project_id == PROJECT_ID
        assert task.project_deadline == PROJECT_DEADLINE


class TestDeadlineConstraint:

    def test_deadline_within_project_deadline_is_valid(self):
        task = make_linked_task(
            deadline=PROJECT_DEADLINE - timedelta(days=1)
        )
        assert task.deadline < PROJECT_DEADLINE

    def test_deadline_equal_to_project_deadline_is_valid(self):
        task = make_linked_task(deadline=PROJECT_DEADLINE)
        assert task.deadline == PROJECT_DEADLINE

    def test_deadline_exceeding_project_deadline_raises(self):
        with pytest.raises(DeadlineViolationError):
            make_linked_task(
                deadline=PROJECT_DEADLINE + timedelta(days=1)
            )

    def test_task_without_project_has_no_deadline_constraint(self):
        task = make_task(deadline=datetime(2099, 12, 31))
        assert task.deadline == datetime(2099, 12, 31)

    def test_error_message_includes_both_deadlines(self):
        with pytest.raises(DeadlineViolationError, match="2025"):
            make_linked_task(
                deadline=PROJECT_DEADLINE + timedelta(days=1)
            )



class TestMarkComplete:

    def test_sets_completed_to_true(self):
        task = make_task()
        task.mark_complete()
        assert task.completed is True

    def test_updates_updated_at(self):
        task = make_task()
        before = task.updated_at
        task.mark_complete()
        assert task.updated_at >= before

    def test_emits_task_completed_event(self):
        task = make_task(title="Deploy app")
        task.mark_complete()
        events = task.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskCompleted)

    def test_event_carries_task_id_and_title(self):
        task = make_task(title="Deploy app")
        task.mark_complete()
        event = task.pull_events()[0]
        assert event.task_id == task.id
        assert event.task_title == "Deploy app"

    def test_raises_if_already_completed(self):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        with pytest.raises(TaskAlreadyCompletedError):
            task.mark_complete()



class TestReopen:

    def test_sets_completed_to_false(self):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        task.reopen()
        assert task.completed is False

    def test_updates_updated_at(self):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        before = task.updated_at
        task.reopen()
        assert task.updated_at >= before

    def test_emits_task_reopened_event(self):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        task.reopen()
        events = task.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskReopened)

    def test_event_carries_task_id(self):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        task.reopen()
        event = task.pull_events()[0]
        assert event.task_id == task.id

    def test_event_carries_project_id_when_linked(self):
        task = make_linked_task()
        task.mark_complete()
        task.pull_events()
        task.reopen()
        event = task.pull_events()[0]
        assert event.project_id == PROJECT_ID

    def test_event_project_id_is_none_when_not_linked(self):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        task.reopen()
        event = task.pull_events()[0]
        assert event.project_id is None

    def test_can_be_completed_again_after_reopen(self):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        task.reopen()
        task.pull_events()
        task.mark_complete()
        assert task.completed is True


class TestUpdate:

    def test_updates_title(self):
        task = make_task(title="Old")
        task.update(title="New")
        assert task.title == "New"

    def test_updates_description(self):
        task = make_task()
        task.update(description="Details")
        assert task.description == "Details"

    def test_updates_deadline(self):
        task = make_task(deadline=datetime(2025, 10, 1))
        task.update(deadline=datetime(2025, 9, 1))
        assert task.deadline == datetime(2025, 9, 1)

    def test_updates_all_fields_together(self):
        task = make_task(title="Old", deadline=datetime(2025, 10, 1))
        task.update(
            title="New",
            description="Details",
            deadline=datetime(2025, 9, 1),
        )
        assert task.title == "New"
        assert task.description == "Details"
        assert task.deadline == datetime(2025, 9, 1)

    def test_raises_if_no_fields_provided(self):
        with pytest.raises(InvalidOperationError):
            make_task().update()

    def test_raises_if_deadline_exceeds_project_deadline(self):
        task = make_linked_task(deadline=datetime(2025, 10, 1))
        with pytest.raises(DeadlineViolationError):
            task.update(deadline=PROJECT_DEADLINE + timedelta(days=1))

    def test_deadline_rolled_back_after_violation(self):
        original = datetime(2025, 10, 1)
        task = make_linked_task(deadline=original)
        with pytest.raises(DeadlineViolationError):
            task.update(deadline=PROJECT_DEADLINE + timedelta(days=1))
        assert task.deadline == original

    def test_updates_updated_at(self):
        task = make_task()
        before = task.updated_at
        task.update(title="New")
        assert task.updated_at >= before

    def test_update_emits_no_events(self):
        task = make_task()
        task.update(title="New")
        assert task.pull_events() == []



class TestLinkToProject:

    def test_sets_project_id(self):
        task = make_task()
        task.link_to_project(PROJECT_ID, PROJECT_DEADLINE)
        assert task.project_id == PROJECT_ID

    def test_sets_project_deadline(self):
        task = make_task()
        task.link_to_project(PROJECT_ID, PROJECT_DEADLINE)
        assert task.project_deadline == PROJECT_DEADLINE

    def test_updates_updated_at(self):
        task = make_task()
        before = task.updated_at
        task.link_to_project(PROJECT_ID, PROJECT_DEADLINE)
        assert task.updated_at >= before

    def test_raises_if_task_deadline_exceeds_project(self):
        task = make_task(deadline=PROJECT_DEADLINE + timedelta(days=1))
        with pytest.raises(DeadlineViolationError):
            task.link_to_project(PROJECT_ID, PROJECT_DEADLINE)

    def test_valid_deadline_link_succeeds(self):
        task = make_task(deadline=PROJECT_DEADLINE - timedelta(days=1))
        task.link_to_project(PROJECT_ID, PROJECT_DEADLINE)
        assert task.project_id == PROJECT_ID



class TestUnlinkFromProject:

    def test_clears_project_id(self):
        task = make_linked_task()
        task.unlink_from_project()
        assert task.project_id is None

    def test_clears_project_deadline(self):
        task = make_linked_task()
        task.unlink_from_project()
        assert task.project_deadline is None

    def test_updates_updated_at(self):
        task = make_linked_task()
        before = task.updated_at
        task.unlink_from_project()
        assert task.updated_at >= before

    def test_task_can_have_any_deadline_after_unlink(self):
        task = make_linked_task(deadline=PROJECT_DEADLINE)
        task.unlink_from_project()
        task.update(deadline=datetime(2099, 12, 31))
        assert task.deadline == datetime(2099, 12, 31)



class TestPullEvents:

    def test_returns_pending_events(self):
        task = make_task()
        task.mark_complete()
        assert len(task.pull_events()) == 1

    def test_clears_events_after_pull(self):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        assert task.pull_events() == []

    def test_fresh_task_has_no_events(self):
        assert make_task().pull_events() == []

    def test_multiple_events_all_returned(self):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        task.reopen()
        task.pull_events()
        task.mark_complete()
        task.pull_events()
        task.reopen()
        events = task.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskReopened)