"""
Unit tests for the Project domain entity.
"""
import pytest
from datetime import timedelta
from uuid import UUID

from src.domain.events.events import ProjectCompleted, ProjectDeadlineChanged
from src.domain.exceptions.exceptions import (
    InvalidOperationError,
    ProjectCompletionError,
)



class TestProjectCreate:

    def test_creates_with_title_and_deadline(self, make_project, now):
        deadline = now + timedelta(days=10)
        project = make_project(title="Launch", deadline=deadline)
        assert project.title == "Launch"
        assert project.deadline == deadline

    def test_id_is_auto_generated(self, make_project):
        assert isinstance(make_project().id, UUID)

    def test_two_projects_have_unique_ids(self, make_project):
        assert make_project().id != make_project().id

    def test_completed_defaults_to_false(self, make_project):
        assert make_project().completed is False

    def test_created_at_is_set(self, make_project):
        assert make_project().created_at is not None

    def test_updated_at_is_set(self, make_project):
        assert make_project().updated_at is not None

    def test_events_list_is_empty_on_creation(self, make_project):
        assert make_project().pull_events() == []



class TestMarkComplete:

    def test_marks_project_as_completed(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        assert project.completed is True

    def test_updates_updated_at(self, make_project):
        project = make_project()
        before = project.updated_at
        project.mark_complete(open_task_count=0)
        assert project.updated_at >= before

    def test_emits_project_completed_event(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        events = project.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectCompleted)
        assert events[0].project_id == project.id

    def test_raises_if_already_completed(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        with pytest.raises(InvalidOperationError):
            project.mark_complete(open_task_count=0)

    def test_raises_if_open_tasks_remain(self, make_project):
        with pytest.raises(ProjectCompletionError):
            make_project().mark_complete(open_task_count=3)

    def test_raises_if_one_open_task_remains(self, make_project):
        with pytest.raises(ProjectCompletionError):
            make_project().mark_complete(open_task_count=1)

    def test_error_message_includes_task_count(self, make_project):
        with pytest.raises(ProjectCompletionError, match="2 task"):
            make_project(title="Launch").mark_complete(open_task_count=2)

    def test_already_completed_checked_before_task_count(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        with pytest.raises(InvalidOperationError):
            project.mark_complete(open_task_count=5)



class TestReopen:

    def test_sets_completed_to_false(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        project.reopen()
        assert project.completed is False

    def test_updates_updated_at(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        before = project.updated_at
        project.reopen()
        assert project.updated_at >= before

    def test_emits_no_events(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        project.reopen()
        assert project.pull_events() == []

    def test_can_be_completed_again_after_reopen(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        project.reopen()
        project.mark_complete(open_task_count=0)
        assert project.completed is True



class TestUpdate:

    def test_updates_title(self, make_project):
        project = make_project(title="Old")
        project.update(title="New")
        assert project.title == "New"

    def test_updates_deadline(self, make_project, project_deadline, now):
        project = make_project(deadline=project_deadline)
        new_deadline = project_deadline - timedelta(days=5)
        project.update(deadline=new_deadline)
        assert project.deadline == new_deadline

    def test_updates_title_and_deadline_together(self, make_project, project_deadline):
        project = make_project(title="Old", deadline=project_deadline)
        earlier = project_deadline - timedelta(days=10)
        project.update(title="New", deadline=earlier)
        assert project.title == "New"
        assert project.deadline == earlier

    def test_raises_if_no_fields_provided(self, make_project):
        with pytest.raises(InvalidOperationError):
            make_project().update()

    def test_earlier_deadline_emits_project_deadline_changed(self, make_project, project_deadline):
        project = make_project(deadline=project_deadline)
        project.update(deadline=project_deadline - timedelta(days=5))
        events = project.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectDeadlineChanged)

    def test_deadline_changed_event_has_correct_values(self, make_project, project_deadline):
        old = project_deadline
        new = project_deadline - timedelta(days=5)
        project = make_project(deadline=old)
        project.update(deadline=new)
        event = project.pull_events()[0]
        assert event.project_id == project.id
        assert event.old_deadline == old
        assert event.new_deadline == new

    def test_later_deadline_emits_no_event(self, make_project, project_deadline):
        project = make_project(deadline=project_deadline)
        project.update(deadline=project_deadline + timedelta(days=5))
        assert project.pull_events() == []

    def test_same_deadline_emits_no_event(self, make_project, project_deadline):
        project = make_project(deadline=project_deadline)
        project.update(deadline=project_deadline)
        assert project.pull_events() == []

    def test_only_title_update_emits_no_event(self, make_project):
        project = make_project()
        project.update(title="New title")
        assert project.pull_events() == []

    def test_updates_updated_at(self, make_project):
        project = make_project()
        before = project.updated_at
        project.update(title="New")
        assert project.updated_at >= before



class TestPullEvents:

    def test_returns_pending_events(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        assert len(project.pull_events()) == 1

    def test_clears_events_after_pull(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        assert project.pull_events() == []

    def test_fresh_project_has_no_events(self, make_project):
        assert make_project().pull_events() == []

    def test_multiple_events_all_returned(self, make_project, project_deadline):
        project = make_project(deadline=project_deadline)
        project.update(deadline=project_deadline - timedelta(days=5))
        project.update(deadline=project_deadline - timedelta(days=10))
        events = project.pull_events()
        assert len(events) == 2
        assert all(isinstance(e, ProjectDeadlineChanged) for e in events)