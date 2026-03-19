"""
Unit tests for the Project domain entity.
"""
import pytest
from datetime import datetime
from uuid import UUID

from src.domain.entities.project import Project
from src.domain.events.events import ProjectCompleted, ProjectDeadlineChanged
from src.domain.exceptions.exceptions import (
    InvalidOperationError,
    ProjectCompletionError,
)



def make_project(**kwargs) -> Project:
    defaults = dict(
        title="Test project",
        deadline=datetime(2025, 12, 31),
    )
    return Project.create(**{**defaults, **kwargs})



class TestProjectCreate:

    def test_creates_with_title_and_deadline(self):
        project = make_project(title="Launch", deadline=datetime(2025, 12, 1))
        assert project.title == "Launch"
        assert project.deadline == datetime(2025, 12, 1)

    def test_id_is_auto_generated(self):
        project = make_project()
        assert isinstance(project.id, UUID)

    def test_two_projects_have_unique_ids(self):
        assert make_project().id != make_project().id

    def test_completed_defaults_to_false(self):
        assert make_project().completed is False

    def test_created_at_is_set(self):
        assert make_project().created_at is not None

    def test_updated_at_is_set(self):
        assert make_project().updated_at is not None

    def test_events_list_is_empty_on_creation(self):
        assert make_project().pull_events() == []



class TestMarkComplete:

    def test_marks_project_as_completed(self):
        project = make_project()
        project.mark_complete(open_task_count=0)
        assert project.completed is True

    def test_updates_updated_at(self):
        project = make_project()
        before = project.updated_at
        project.mark_complete(open_task_count=0)
        assert project.updated_at >= before

    def test_emits_project_completed_event(self):
        project = make_project()
        project.mark_complete(open_task_count=0)
        events = project.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectCompleted)
        assert events[0].project_id == project.id

    def test_raises_if_already_completed(self):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        with pytest.raises(InvalidOperationError):
            project.mark_complete(open_task_count=0)

    def test_raises_if_open_tasks_remain(self):
        project = make_project()
        with pytest.raises(ProjectCompletionError):
            project.mark_complete(open_task_count=3)

    def test_raises_if_one_open_task_remains(self):
        project = make_project()
        with pytest.raises(ProjectCompletionError):
            project.mark_complete(open_task_count=1)

    def test_error_message_includes_task_count(self):
        project = make_project(title="Launch")
        with pytest.raises(ProjectCompletionError, match="2 task"):
            project.mark_complete(open_task_count=2)

    def test_already_completed_checked_before_task_count(self):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        # even with open tasks, already-completed check fires first
        with pytest.raises(InvalidOperationError):
            project.mark_complete(open_task_count=5)


class TestReopen:

    def test_sets_completed_to_false(self):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        project.reopen()
        assert project.completed is False

    def test_updates_updated_at(self):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        before = project.updated_at
        project.reopen()
        assert project.updated_at >= before

    def test_emits_no_events(self):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        project.reopen()
        assert project.pull_events() == []

    def test_can_be_completed_again_after_reopen(self):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        project.reopen()
        project.mark_complete(open_task_count=0)
        assert project.completed is True



class TestUpdate:

    def test_updates_title(self):
        project = make_project(title="Old")
        project.update(title="New")
        assert project.title == "New"

    def test_updates_deadline(self):
        project = make_project(deadline=datetime(2025, 12, 31))
        new_deadline = datetime(2025, 12, 15)
        project.update(deadline=new_deadline)
        assert project.deadline == new_deadline

    def test_updates_title_and_deadline_together(self):
        project = make_project(title="Old", deadline=datetime(2025, 12, 31))
        project.update(title="New", deadline=datetime(2025, 11, 1))
        assert project.title == "New"
        assert project.deadline == datetime(2025, 11, 1)

    def test_raises_if_no_fields_provided(self):
        project = make_project()
        with pytest.raises(InvalidOperationError):
            project.update()

    def test_earlier_deadline_emits_project_deadline_changed(self):
        project = make_project(deadline=datetime(2025, 12, 31))
        project.update(deadline=datetime(2025, 11, 1))
        events = project.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectDeadlineChanged)

    def test_deadline_changed_event_has_correct_values(self):
        old = datetime(2025, 12, 31)
        new = datetime(2025, 11, 1)
        project = make_project(deadline=old)
        project.update(deadline=new)
        event = project.pull_events()[0]
        assert event.project_id == project.id
        assert event.old_deadline == old
        assert event.new_deadline == new

    def test_later_deadline_emits_no_event(self):
        project = make_project(deadline=datetime(2025, 11, 1))
        project.update(deadline=datetime(2025, 12, 31))
        assert project.pull_events() == []

    def test_same_deadline_emits_no_event(self):
        deadline = datetime(2025, 12, 31)
        project = make_project(deadline=deadline)
        project.update(deadline=deadline)
        assert project.pull_events() == []

    def test_only_title_update_emits_no_event(self):
        project = make_project()
        project.update(title="New title")
        assert project.pull_events() == []

    def test_updates_updated_at(self):
        project = make_project()
        before = project.updated_at
        project.update(title="New")
        assert project.updated_at >= before



class TestPullEvents:

    def test_returns_pending_events(self):
        project = make_project()
        project.mark_complete(open_task_count=0)
        assert len(project.pull_events()) == 1

    def test_clears_events_after_pull(self):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        assert project.pull_events() == []

    def test_fresh_project_has_no_events(self):
        assert make_project().pull_events() == []

    def test_multiple_events_all_returned(self):
        project = make_project(deadline=datetime(2025, 12, 31))
        project.update(deadline=datetime(2025, 10, 1))
        project.update(deadline=datetime(2025, 9, 1))
        events = project.pull_events()
        assert len(events) == 2
        assert all(isinstance(e, ProjectDeadlineChanged) for e in events)