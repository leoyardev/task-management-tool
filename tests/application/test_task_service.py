"""
Unit tests for TaskService.

All dependencies are mocked — no database, no framework.
Tests verify orchestration logic only, not domain rules
(those are covered in domain unit tests).
"""
import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import create_autospec, MagicMock
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
from src.domain.entities.project import Project
from src.domain.entities.task import Task
from src.domain.ports.notification import NotificationPort
from src.domain.ports.project import ProjectRepository
from src.domain.ports.task import TaskRepository



NOW = datetime.now(UTC)
PROJECT_DEADLINE = NOW + timedelta(days=30)
PROJECT_ID = uuid4()


def make_task(**kwargs) -> Task:
    defaults = dict(title="Test task", deadline=NOW + timedelta(days=7))
    return Task.create(**{**defaults, **kwargs})


def make_project(**kwargs) -> Project:
    defaults = dict(title="Test project", deadline=PROJECT_DEADLINE)
    return Project.create(**{**defaults, **kwargs})


def make_linked_task(**kwargs) -> Task:
    return make_task(
        project_id=PROJECT_ID,
        project_deadline=PROJECT_DEADLINE,
        **kwargs,
    )


@pytest.fixture
def task_repo():
    return create_autospec(TaskRepository)


@pytest.fixture
def project_repo():
    return create_autospec(ProjectRepository)


@pytest.fixture
def notification():
    return create_autospec(NotificationPort)


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

    def test_returns_task_when_found(self, service, task_repo):
        task = make_task()
        task_repo.find_by_id.return_value = task
        assert service.get_task(task.id) == task

    def test_raises_not_found_when_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.get_task(uuid4())



class TestGetAllTasks:

    def test_returns_all_tasks(self, service, task_repo):
        tasks = [make_task(), make_task()]
        task_repo.find_all.return_value = tasks
        assert service.get_all_tasks() == tasks

    def test_passes_spec_to_repository(self, service, task_repo):
        spec = MagicMock()
        task_repo.find_all.return_value = []
        service.get_all_tasks(spec)
        task_repo.find_all.assert_called_once_with(spec)




class TestCreateTask:

    def test_saves_and_returns_task(self, service, task_repo, project_repo):
        dto = CreateTaskDTO(title="New task", deadline=NOW + timedelta(days=7))
        task = make_task(title="New task")
        task_repo.save.return_value = task
        result = service.create_task(dto)
        assert task_repo.save.called
        assert result == task

    def test_creates_task_with_correct_title(self, service, task_repo, project_repo):
        dto = CreateTaskDTO(title="My task", deadline=NOW + timedelta(days=7))
        task_repo.save.side_effect = lambda t: t
        result = service.create_task(dto)
        assert result.title == "My task"

    def test_fetches_project_deadline_when_project_id_given(
        self, service, task_repo, project_repo
    ):
        project = make_project()
        dto = CreateTaskDTO(
            title="Task",
            deadline=NOW + timedelta(days=7),
            project_id=project.id,
        )
        project_repo.find_by_id.return_value = project
        task_repo.save.side_effect = lambda t: t
        result = service.create_task(dto)
        project_repo.find_by_id.assert_called_once_with(project.id)
        assert result.project_deadline == project.deadline

    def test_raises_not_found_if_project_missing(self, service, task_repo, project_repo):
        project_repo.find_by_id.return_value = None
        dto = CreateTaskDTO(
            title="Task",
            deadline=NOW + timedelta(days=7),
            project_id=uuid4(),
        )
        with pytest.raises(NotFoundError):
            service.create_task(dto)

    def test_raises_deadline_violation_if_exceeds_project(
        self, service, task_repo, project_repo
    ):
        project = make_project(deadline=NOW + timedelta(days=5))
        project_repo.find_by_id.return_value = project
        dto = CreateTaskDTO(
            title="Task",
            deadline=NOW + timedelta(days=10),  # exceeds project
            project_id=project.id,
        )
        with pytest.raises(DeadlineViolationError):
            service.create_task(dto)



class TestUpdateTask:

    def test_updates_title(self, service, task_repo):
        task = make_task(title="Old")
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        result = service.update_task(task.id, UpdateTaskDTO(title="New"))
        assert result.title == "New"

    def test_raises_not_found_if_task_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.update_task(uuid4(), UpdateTaskDTO(title="New"))

    def test_raises_if_no_fields_provided(self, service, task_repo):
        task = make_task()
        task_repo.find_by_id.return_value = task
        with pytest.raises(InvalidOperationError):
            service.update_task(task.id, UpdateTaskDTO())

    def test_raises_deadline_violation_on_invalid_deadline(self, service, task_repo):
        task = make_linked_task(deadline=NOW + timedelta(days=5))
        task_repo.find_by_id.return_value = task
        with pytest.raises(DeadlineViolationError):
            service.update_task(
                task.id,
                UpdateTaskDTO(deadline=PROJECT_DEADLINE + timedelta(days=1)),
            )



class TestDeleteTask:

    def test_deletes_task(self, service, task_repo):
        task = make_task()
        task_repo.find_by_id.return_value = task
        service.delete_task(task.id)
        task_repo.delete.assert_called_once_with(task.id)

    def test_raises_not_found_if_task_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.delete_task(uuid4())



class TestCompleteTask:

    def test_completes_task(self, service, task_repo):
        task = make_task()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        result = service.complete_task(task.id)
        assert result.completed is True

    def test_raises_not_found_if_task_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.complete_task(uuid4())

    def test_raises_if_already_completed(self, service, task_repo):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        task_repo.find_by_id.return_value = task
        with pytest.raises(TaskAlreadyCompletedError):
            service.complete_task(task.id)

    def test_notifies_task_completed_event(self, service, task_repo, notification):
        task = make_task()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        service.complete_task(task.id)
        notification.notify.assert_called_once()
        assert isinstance(notification.notify.call_args[0][0], TaskCompleted)

    def test_auto_complete_disabled_does_not_complete_project(
        self, service, task_repo, project_repo
    ):
        task = make_linked_task()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        task_repo.count_open_by_project.return_value = 0
        service.complete_task(task.id)
        project_repo.find_by_id.assert_not_called()

    def test_auto_complete_enabled_completes_project_when_last_task_done(
        self, service_auto_complete, task_repo, project_repo, notification
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
        self, service_auto_complete, task_repo, project_repo
    ):
        project = make_project()
        task = make_task(project_id=project.id, project_deadline=project.deadline)
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        task_repo.count_open_by_project.return_value = 2
        service_auto_complete.complete_task(task.id)
        project_repo.save.assert_not_called()



class TestReopenTask:

    def test_reopens_task(self, service, task_repo):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        result = service.reopen_task(task.id)
        assert result.completed is False

    def test_raises_not_found_if_task_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.reopen_task(uuid4())

    def test_reopens_completed_project_when_task_reopened(
        self, service, task_repo, project_repo, notification
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
        self, service, task_repo, project_repo
    ):
        project = make_project()  # not completed
        task = make_task(project_id=project.id, project_deadline=project.deadline)
        task.mark_complete()
        task.pull_events()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        project_repo.find_by_id.return_value = project
        service.reopen_task(task.id)
        project_repo.save.assert_not_called()



class TestLinkToProject:

    def test_links_task_to_project(self, service, task_repo, project_repo):
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

    def test_raises_not_found_if_project_missing(self, service, task_repo, project_repo):
        task = make_task()
        task_repo.find_by_id.return_value = task
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.link_to_project(task.id, uuid4())

    def test_raises_deadline_violation_if_task_exceeds_project(
        self, service, task_repo, project_repo
    ):
        project = make_project(deadline=NOW + timedelta(days=5))
        task = make_task(deadline=NOW + timedelta(days=10))
        task_repo.find_by_id.return_value = task
        project_repo.find_by_id.return_value = project
        with pytest.raises(DeadlineViolationError):
            service.link_to_project(task.id, project.id)



class TestUnlinkFromProject:

    def test_unlinks_task_from_project(self, service, task_repo):
        task = make_linked_task()
        task_repo.find_by_id.return_value = task
        task_repo.save.side_effect = lambda t: t
        result = service.unlink_from_project(task.id)
        assert result.project_id is None

    def test_raises_not_found_if_task_missing(self, service, task_repo):
        task_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.unlink_from_project(uuid4())