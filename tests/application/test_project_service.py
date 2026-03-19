"""
Unit tests for ProjectService.

All dependencies are mocked — no database, no framework.
"""
import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import create_autospec
from uuid import uuid4

from src.application.dtos import CreateProjectDTO, UpdateProjectDTO
from src.application.project_service import ProjectService
from src.domain.events.events import ProjectCompleted, ProjectDeadlineChanged
from src.domain.exceptions.exceptions import (
    InvalidOperationError,
    NotFoundError,
    ProjectCompletionError,
)
from src.domain.entities.project import Project
from src.domain.entities.task import Task
from src.domain.ports.notification import NotificationPort
from src.domain.ports.project import ProjectRepository
from src.domain.ports.task import TaskRepository


NOW = datetime.now(UTC)
PROJECT_DEADLINE = NOW + timedelta(days=30)


def make_project(**kwargs) -> Project:
    defaults = dict(title="Test project", deadline=PROJECT_DEADLINE)
    return Project.create(**{**defaults, **kwargs})


def make_task(**kwargs) -> Task:
    defaults = dict(title="Test task", deadline=NOW + timedelta(days=7))
    return Task.create(**{**defaults, **kwargs})


@pytest.fixture
def project_repo():
    return create_autospec(ProjectRepository)


@pytest.fixture
def task_repo():
    return create_autospec(TaskRepository)


@pytest.fixture
def notification():
    return create_autospec(NotificationPort)


@pytest.fixture
def service(project_repo, task_repo, notification):
    return ProjectService(
        project_repo=project_repo,
        task_repo=task_repo,
        notification=notification,
    )


class TestGetProject:

    def test_returns_project_when_found(self, service, project_repo):
        project = make_project()
        project_repo.find_by_id.return_value = project
        result = service.get_project(project.id)
        assert result == project

    def test_raises_not_found_when_missing(self, service, project_repo):
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.get_project(uuid4())


class TestGetAllProjects:

    def test_returns_all_projects(self, service, project_repo):
        projects = [make_project(), make_project()]
        project_repo.find_all.return_value = projects
        result = service.get_all_projects()
        assert result == projects

    def test_returns_empty_list_when_none(self, service, project_repo):
        project_repo.find_all.return_value = []
        assert service.get_all_projects() == []



class TestGetProjectTasks:

    def test_returns_tasks_for_project(self, service, project_repo, task_repo):
        project = make_project()
        tasks = [make_task(), make_task()]
        project_repo.find_by_id.return_value = project
        task_repo.find_all.return_value = tasks
        result = service.get_project_tasks(project.id)
        assert result == tasks

    def test_raises_not_found_if_project_missing(self, service, project_repo):
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.get_project_tasks(uuid4())



class TestCreateProject:

    def test_saves_and_returns_project(self, service, project_repo):
        dto = CreateProjectDTO(title="New project", deadline=PROJECT_DEADLINE)
        project = make_project(title="New project")
        project_repo.save.return_value = project
        result = service.create_project(dto)
        assert project_repo.save.called
        assert result == project

    def test_project_created_with_correct_title(self, service, project_repo):
        dto = CreateProjectDTO(title="My project", deadline=PROJECT_DEADLINE)
        project_repo.save.side_effect = lambda p: p
        result = service.create_project(dto)
        assert result.title == "My project"

    def test_project_created_with_correct_deadline(self, service, project_repo):
        dto = CreateProjectDTO(title="My project", deadline=PROJECT_DEADLINE)
        project_repo.save.side_effect = lambda p: p
        result = service.create_project(dto)
        assert result.deadline == PROJECT_DEADLINE



class TestUpdateProject:

    def test_updates_title(self, service, project_repo, task_repo):
        project = make_project(title="Old")
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        dto = UpdateProjectDTO(title="New")
        result = service.update_project(project.id, dto)
        assert result.title == "New"

    def test_raises_not_found_if_project_missing(self, service, project_repo):
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.update_project(uuid4(), UpdateProjectDTO(title="New"))

    def test_raises_if_no_fields_provided(self, service, project_repo):
        project = make_project()
        project_repo.find_by_id.return_value = project
        with pytest.raises(InvalidOperationError):
            service.update_project(project.id, UpdateProjectDTO())

    def test_notifies_on_deadline_change(self, service, project_repo, task_repo, notification):
        project = make_project(deadline=PROJECT_DEADLINE)
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        task_repo.find_exceeding_deadline.return_value = []
        earlier = PROJECT_DEADLINE - timedelta(days=5)
        service.update_project(project.id, UpdateProjectDTO(deadline=earlier))
        notification.notify.assert_called_once()
        event = notification.notify.call_args[0][0]
        assert isinstance(event, ProjectDeadlineChanged)

    def test_cascades_deadline_to_affected_tasks(self, service, project_repo, task_repo, notification):
        project = make_project(deadline=PROJECT_DEADLINE)
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        affected_task = make_task(
            deadline=PROJECT_DEADLINE,
            project_id=project.id,
            project_deadline=PROJECT_DEADLINE,
        )
        earlier = PROJECT_DEADLINE - timedelta(days=5)
        task_repo.find_exceeding_deadline.return_value = [affected_task]
        service.update_project(project.id, UpdateProjectDTO(deadline=earlier))
        task_repo.save.assert_called_once_with(affected_task)

    def test_no_cascade_when_deadline_moves_later(self, service, project_repo, task_repo, notification):
        project = make_project(deadline=PROJECT_DEADLINE)
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        later = PROJECT_DEADLINE + timedelta(days=5)
        service.update_project(project.id, UpdateProjectDTO(deadline=later))
        task_repo.find_exceeding_deadline.assert_not_called()
        notification.notify.assert_not_called()



class TestDeleteProject:

    def test_deletes_project(self, service, project_repo):
        project = make_project()
        project_repo.find_by_id.return_value = project
        service.delete_project(project.id)
        project_repo.delete.assert_called_once_with(project.id)

    def test_raises_not_found_if_project_missing(self, service, project_repo):
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.delete_project(uuid4())



class TestCompleteProject:

    def test_completes_project_with_no_open_tasks(self, service, project_repo, task_repo, notification):
        project = make_project()
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        task_repo.count_open_by_project.return_value = 0
        result = service.complete_project(project.id)
        assert result.completed is True

    def test_raises_if_open_tasks_remain(self, service, project_repo, task_repo):
        project = make_project()
        project_repo.find_by_id.return_value = project
        task_repo.count_open_by_project.return_value = 2
        with pytest.raises(ProjectCompletionError):
            service.complete_project(project.id)

    def test_notifies_project_completed_event(self, service, project_repo, task_repo, notification):
        project = make_project()
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        task_repo.count_open_by_project.return_value = 0
        service.complete_project(project.id)
        notification.notify.assert_called_once()
        event = notification.notify.call_args[0][0]
        assert isinstance(event, ProjectCompleted)

    def test_raises_not_found_if_project_missing(self, service, project_repo):
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.complete_project(uuid4())