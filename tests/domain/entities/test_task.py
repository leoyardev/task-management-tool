"""
Unit tests for the Task domain entity.
"""

from datetime import timedelta
from uuid import UUID

import pytest

from src.domain.events.events import TaskCompleted, TaskReopened
from src.domain.exceptions.exceptions import (
    DeadlineViolationError,
    InvalidOperationError,
    TaskAlreadyCompletedError,
)


class TestTaskCreate:
    def test_creates_with_required_fields(self, make_task, now):
        deadline = now + timedelta(days=3)
        task = make_task(title="Deploy", deadline=deadline)
        assert task.title == "Deploy"
        assert task.deadline == deadline

    def test_id_is_auto_generated(self, make_task):
        assert isinstance(make_task().id, UUID)

    def test_two_tasks_have_unique_ids(self, make_task):
        assert make_task().id != make_task().id

    def test_completed_defaults_to_false(self, make_task):
        assert make_task().completed is False

    def test_description_defaults_to_none(self, make_task):
        assert make_task().description is None

    def test_project_id_defaults_to_none(self, make_task):
        assert make_task().project_id is None

    def test_project_deadline_defaults_to_none(self, make_task):
        assert make_task().project_deadline is None

    def test_created_at_is_set(self, make_task):
        assert make_task().created_at is not None

    def test_updated_at_is_set(self, make_task):
        assert make_task().updated_at is not None

    def test_events_list_is_empty_on_creation(self, make_task):
        assert make_task().pull_events() == []

    def test_creates_with_description(self, make_task):
        assert make_task(description="Some details").description == "Some details"

    def test_creates_with_project_linked(
        self, make_linked_task, project_id, project_deadline
    ):
        task = make_linked_task(
            project_id=project_id, project_deadline=project_deadline
        )
        assert task.project_id == project_id
        assert task.project_deadline == project_deadline


class TestDeadlineConstraint:
    def test_deadline_within_project_deadline_is_valid(
        self, make_linked_task, project_deadline
    ):
        task = make_linked_task(deadline=project_deadline - timedelta(days=1))
        assert task.deadline < project_deadline

    def test_deadline_equal_to_project_deadline_is_valid(
        self, make_linked_task, project_deadline
    ):
        task = make_linked_task(deadline=project_deadline)
        assert task.deadline == project_deadline

    def test_deadline_exceeding_project_deadline_raises(
        self, make_linked_task, project_deadline
    ):
        with pytest.raises(DeadlineViolationError):
            make_linked_task(deadline=project_deadline + timedelta(days=1))

    def test_task_without_project_has_no_deadline_constraint(self, make_task, now):
        far_future = now + timedelta(days=9999)
        task = make_task(deadline=far_future)
        assert task.deadline == far_future

    def test_error_message_includes_deadline(self, make_linked_task, project_deadline):
        with pytest.raises(DeadlineViolationError, match="exceeds project deadline"):
            make_linked_task(deadline=project_deadline + timedelta(days=1))


class TestMarkComplete:
    def test_sets_completed_to_true(self, make_task):
        task = make_task()
        task.mark_complete()
        assert task.completed is True

    def test_updates_updated_at(self, make_task):
        task = make_task()
        before = task.updated_at
        task.mark_complete()
        assert task.updated_at >= before

    def test_emits_task_completed_event(self, make_task, task_title):
        task = make_task(title=task_title)
        task.mark_complete()
        events = task.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskCompleted)

    def test_event_carries_task_id_and_title(self, make_task, task_title):
        task = make_task(title=task_title)
        task.mark_complete()
        event = task.pull_events()[0]
        assert event.task_id == task.id
        assert event.task_title == task_title

    def test_raises_if_already_completed(self, make_completed_task):
        task = make_completed_task()
        with pytest.raises(TaskAlreadyCompletedError):
            task.mark_complete()


class TestReopen:
    def test_sets_completed_to_false(self, make_completed_task):
        task = make_completed_task()
        task.reopen()
        assert task.completed is False

    def test_updates_updated_at(self, make_completed_task):
        task = make_completed_task()
        before = task.updated_at
        task.reopen()
        assert task.updated_at >= before

    def test_emits_task_reopened_event(self, make_completed_task):
        task = make_completed_task()
        task.reopen()
        events = task.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskReopened)

    def test_event_carries_task_id(self, make_completed_task):
        task = make_completed_task()
        task.reopen()
        assert task.pull_events()[0].task_id == task.id

    def test_event_carries_project_id_when_linked(
        self, make_linked_task, project_id, project_deadline
    ):
        task = make_linked_task(
            project_id=project_id, project_deadline=project_deadline
        )
        task.mark_complete()
        task.pull_events()
        task.reopen()
        assert task.pull_events()[0].project_id == project_id

    def test_event_project_id_is_none_when_not_linked(self, make_completed_task):
        task = make_completed_task()
        task.reopen()
        assert task.pull_events()[0].project_id is None

    def test_can_be_completed_again_after_reopen(self, make_completed_task):
        task = make_completed_task()
        task.reopen()
        task.pull_events()
        task.mark_complete()
        assert task.completed is True


class TestUpdate:
    def test_updates_title(self, make_task):
        task = make_task(title="Old")
        task.update(title="New")
        assert task.title == "New"

    def test_updates_description(self, make_task):
        task = make_task()
        task.update(description="Details")
        assert task.description == "Details"

    def test_updates_deadline(self, make_task, now):
        earlier = now + timedelta(days=3)
        later = now + timedelta(days=5)
        task = make_task(deadline=later)
        task.update(deadline=earlier)
        assert task.deadline == earlier

    def test_updates_all_fields_together(self, make_task, now):
        later = now + timedelta(days=5)
        earlier = now + timedelta(days=3)
        task = make_task(title="Old", deadline=later)
        task.update(title="New", description="Details", deadline=earlier)
        assert task.title == "New"
        assert task.description == "Details"
        assert task.deadline == earlier

    def test_raises_if_no_fields_provided(self, make_task):
        with pytest.raises(InvalidOperationError):
            make_task().update()

    def test_raises_if_deadline_exceeds_project_deadline(
        self, make_linked_task, project_deadline, now
    ):
        task = make_linked_task(deadline=now + timedelta(days=5))
        with pytest.raises(DeadlineViolationError):
            task.update(deadline=project_deadline + timedelta(days=1))

    def test_deadline_rolled_back_after_violation(
        self, make_linked_task, project_deadline, now
    ):
        original = now + timedelta(days=5)
        task = make_linked_task(deadline=original)
        with pytest.raises(DeadlineViolationError):
            task.update(deadline=project_deadline + timedelta(days=1))
        assert task.deadline == original

    def test_updates_updated_at(self, make_task):
        task = make_task()
        before = task.updated_at
        task.update(title="New")
        assert task.updated_at >= before

    def test_update_emits_no_events(self, make_task):
        task = make_task()
        task.update(title="New")
        assert task.pull_events() == []


class TestLinkToProject:
    def test_sets_project_id(self, make_task, project_id, project_deadline):
        task = make_task()
        task.link_to_project(project_id, project_deadline)
        assert task.project_id == project_id

    def test_sets_project_deadline(self, make_task, project_id, project_deadline):
        task = make_task()
        task.link_to_project(project_id, project_deadline)
        assert task.project_deadline == project_deadline

    def test_updates_updated_at(self, make_task, project_id, project_deadline):
        task = make_task()
        before = task.updated_at
        task.link_to_project(project_id, project_deadline)
        assert task.updated_at >= before

    def test_raises_if_task_deadline_exceeds_project(
        self, make_task, project_id, project_deadline
    ):
        task = make_task(deadline=project_deadline + timedelta(days=1))
        with pytest.raises(DeadlineViolationError):
            task.link_to_project(project_id, project_deadline)

    def test_valid_deadline_link_succeeds(
        self, make_task, project_id, project_deadline
    ):
        task = make_task(deadline=project_deadline - timedelta(days=1))
        task.link_to_project(project_id, project_deadline)
        assert task.project_id == project_id


class TestUnlinkFromProject:
    def test_clears_project_id(self, make_linked_task):
        task = make_linked_task()
        task.unlink_from_project()
        assert task.project_id is None

    def test_clears_project_deadline(self, make_linked_task):
        task = make_linked_task()
        task.unlink_from_project()
        assert task.project_deadline is None

    def test_updates_updated_at(self, make_linked_task):
        task = make_linked_task()
        before = task.updated_at
        task.unlink_from_project()
        assert task.updated_at >= before

    def test_task_can_have_any_deadline_after_unlink(
        self, make_linked_task, project_deadline, now
    ):
        task = make_linked_task(deadline=project_deadline)
        task.unlink_from_project()
        far_future = now + timedelta(days=9999)
        task.update(deadline=far_future)
        assert task.deadline == far_future


class TestPullEvents:
    def test_returns_pending_events(self, make_task):
        task = make_task()
        task.mark_complete()
        assert len(task.pull_events()) == 1

    def test_clears_events_after_pull(self, make_task):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        assert task.pull_events() == []

    def test_fresh_task_has_no_events(self, make_task):
        assert make_task().pull_events() == []

    def test_multiple_events_all_returned(self, make_task):
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
