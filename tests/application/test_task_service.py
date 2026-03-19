"""
Unit tests for TaskService.
All dependencies are mocked — no database, no framework.
"""
import pytest
from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from src.application.dtos import CreateTaskDTO, UpdateTaskDTO
from src.application.task_service import TaskService
from src.domain.events.events import TaskCompleted
from src.domain.exceptions.exceptions import (
    NotFoundError,
    InvalidOperationError,
    TaskAlreadyCompletedError,
    DeadlineViolationError,
)


@pytest.fixture
def service(task_repo, project_repo, notification):
    return TaskService(
        task_repo=task_repo,
        project_repo=project_repo,
        notification=notification,
        auto_complete_project=False,
    )
 
 
@pytest.fixture
def service_auto_complete(task_repo, project_repo, notification):
    return TaskService(
        task_repo=task_repo,
        project_repo=project_repo,
        notification=notification,
        auto_complete_project=True,
    )
 
 
 
class TestGetTask:
 
    def test_returns_task_when_found(self, service, task_repo, make_task):
        task = make_task()
        task_repo.find_by_id.return_value = task
        assert service.get_task(task.id) == task
 
    def test_raises_not_found_when_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.get_task(uuid4())
 
 
 
class TestGetAllTasks:
 
    def test_returns_all_tasks(self, service, task_repo, make_task):
        tasks = [make_task(), make_task()]
        task_repo.find_all.return_value = tasks
        assert service.get_all_tasks() == tasks
 
    def test_passes_spec_to_repository(self, service, task_repo):
        spec = MagicMock()
        task_repo.find_all.return_value = []
        service.get_all_tasks(spec)
        task_repo.find_all.assert_called_once_with(spec)
 

 
class TestCreateTask:
 
    def test_saves_and_returns_task(self, service, task_repo, project_repo, make_task, now):
        dto = CreateTaskDTO(title="New task", deadline=now + timedelta(days=7))
        task = make_task(title="New task")
        task_repo.save.return_value = task
        result = service.create_task(dto)
        assert task_repo.save.called
        assert result == task
 
    def test_creates_task_with_correct_title(self, service, task_repo, now):
        dto = CreateTaskDTO(title="My task", deadline=now + timedelta(days=7))
        task_repo.save.side_effect = lambda t: t
        result = service.create_task(dto)
        assert result.title == "My task"
 
    def test_fetches_project_deadline_when_project_id_given(
        self, service, task_repo, project_repo, make_project, now
    ):
        project = make_project()
        dto = CreateTaskDTO(
            title="Task",
            deadline=now + timedelta(days=7),
            project_id=project.id,
        )
        project_repo.find_by_id.return_value = project
        task_repo.save.side_effect = lambda t: t
        result = service.create_task(dto)
        project_repo.find_by_id.assert_called_once_with(project.id)
        assert result.project_deadline == project.deadline
 
    def test_raises_not_found_if_project_missing(self, service, task_repo, project_repo, now):
        project_repo.find_by_id.return_value = None
        dto = CreateTaskDTO(
            title="Task",
            deadline=now + timedelta(days=7),
            project_id=uuid4(),
        )
        with pytest.raises(NotFoundError):
            service.create_task(dto)
 
    def test_raises_deadline_violation_if_exceeds_project(
        self, service, task_repo, project_repo, make_project, now
    ):
        project = make_project(deadline=now + timedelta(days=5))
        project_repo.find_by_id.return_value = project
        dto = CreateTaskDTO(
            title="Task",
            deadline=now + timedelta(days=10),
            project_id=project.id,
        )
        with pytest.raises(DeadlineViolationError):
            service.create_task(dto)
 
 
 
class TestUpdateTask:
 
    def test_updates_title(self, service, task_repo, make_task):
        task = make_task(title="Old")
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        result = service.update_task(task.id, UpdateTaskDTO(title="New"))
        assert result.title == "New"
 
    def test_raises_not_found_if_task_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.update_task(uuid4(), UpdateTaskDTO(title="New"))
 
    def test_raises_if_no_fields_provided(self, service, task_repo, make_task):
        task = make_task()
        task_repo.find_by_id.return_value = task
        with pytest.raises(InvalidOperationError):
            service.update_task(task.id, UpdateTaskDTO())
 
    def test_raises_deadline_violation_on_invalid_deadline(
        self, service, task_repo, make_linked_task, project_deadline, now
    ):
        task = make_linked_task(deadline=now + timedelta(days=5))
        task_repo.find_by_id.return_value = task
        with pytest.raises(DeadlineViolationError):
            service.update_task(
                task.id,
                UpdateTaskDTO(deadline=project_deadline + timedelta(days=1)),
            )
 
 
 
class TestDeleteTask:
 
    def test_deletes_task(self, service, task_repo, make_task):
        task = make_task()
        task_repo.find_by_id.return_value = task
        service.delete_task(task.id)
        task_repo.delete.assert_called_once_with(task.id)
 
    def test_raises_not_found_if_task_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.delete_task(uuid4())
 
 
class TestCompleteTask:
 
    def test_completes_task(self, service, task_repo, make_task):
        task = make_task()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        result = service.complete_task(task.id)
        assert result.completed is True
 
    def test_raises_not_found_if_task_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.complete_task(uuid4())
 
    def test_raises_if_already_completed(self, service, task_repo, make_completed_task):
        task = make_completed_task()
        task_repo.find_by_id.return_value = task
        with pytest.raises(TaskAlreadyCompletedError):
            service.complete_task(task.id)
 
    def test_notifies_task_completed_event(self, service, task_repo, notification, make_task):
        task = make_task()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        service.complete_task(task.id)
        notification.notify.assert_called_once()
        assert isinstance(notification.notify.call_args[0][0], TaskCompleted)
 
    def test_auto_complete_disabled_does_not_complete_project(
        self, service, task_repo, project_repo, make_linked_task
    ):
        task = make_linked_task()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        task_repo.count_open_by_project.return_value = 0
        service.complete_task(task.id)
        project_repo.find_by_id.assert_not_called()
 
    def test_auto_complete_enabled_completes_project_when_last_task_done(
        self, service_auto_complete, task_repo, project_repo, notification, make_task, make_project
    ):
        project = make_project()
        task = make_task(project_id=project.id, project_deadline=project.deadline)
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        task_repo.count_open_by_project.return_value = 0
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        service_auto_complete.complete_task(task.id)
        assert project.completed is True
 
    def test_auto_complete_does_not_complete_project_if_tasks_remain(
        self, service_auto_complete, task_repo, project_repo, make_task, make_project
    ):
        project = make_project()
        task = make_task(project_id=project.id, project_deadline=project.deadline)
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        task_repo.count_open_by_project.return_value = 2
        service_auto_complete.complete_task(task.id)
        project_repo.save.assert_not_called()
 
 
class TestReopenTask:
 
    def test_reopens_task(self, service, task_repo, make_completed_task):
        task = make_completed_task()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        result = service.reopen_task(task.id)
        assert result.completed is False
 
    def test_raises_not_found_if_task_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.reopen_task(uuid4())
 
    def test_reopens_completed_project_when_task_reopened(
        self, service, task_repo, project_repo, notification, make_task, make_project
    ):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        task = make_task(project_id=project.id, project_deadline=project.deadline)
        task.mark_complete()
        task.pull_events()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        service.reopen_task(task.id)
        assert project.completed is False
 
    def test_does_not_reopen_project_if_not_completed(
        self, service, task_repo, project_repo, make_task, make_project
    ):
        project = make_project()
        task = make_task(project_id=project.id, project_deadline=project.deadline)
        task.mark_complete()
        task.pull_events()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        project_repo.find_by_id.return_value = project
        service.reopen_task(task.id)
        project_repo.save.assert_not_called()
 
 
class TestLinkToProject:
 
    def test_links_task_to_project(self, service, task_repo, project_repo, make_task, make_project):
        task = make_task()
        project = make_project()
        task_repo.find_by_id.return_value = task
        project_repo.find_by_id.return_value = project
        task_repo.save.side_effect = lambda t: t
        result = service.link_to_project(task.id, project.id)
        assert result.project_id == project.id
 
    def test_raises_not_found_if_task_missing(self, service, task_repo, project_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.link_to_project(uuid4(), uuid4())
 
    def test_raises_not_found_if_project_missing(self, service, task_repo, project_repo, make_task):
        task = make_task()
        task_repo.find_by_id.return_value = task
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.link_to_project(task.id, uuid4())
 
    def test_raises_deadline_violation_if_task_exceeds_project(
        self, service, task_repo, project_repo, make_task, make_project, now
    ):
        project = make_project(deadline=now + timedelta(days=5))
        task = make_task(deadline=now + timedelta(days=10))
        task_repo.find_by_id.return_value = task
        project_repo.find_by_id.return_value = project
        with pytest.raises(DeadlineViolationError):
            service.link_to_project(task.id, project.id)
 

 
class TestUnlinkFromProject:
 
    def test_unlinks_task_from_project(self, service, task_repo, make_linked_task):
        task = make_linked_task()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        result = service.unlink_from_project(task.id)
        assert result.project_id is None
 
    def test_raises_not_found_if_task_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.unlink_from_project(uuid4())