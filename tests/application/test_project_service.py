"""
Unit tests for ProjectService.
All dependencies are mocked — no database, no framework.
"""
import pytest
from datetime import timedelta
from uuid import uuid4

from src.application.dtos import CreateProjectDTO, UpdateProjectDTO
from src.application.project_service import ProjectService
from src.domain.events.events import ProjectCompleted, ProjectDeadlineChanged
from src.domain.exceptions.exceptions import (
    InvalidOperationError,
    NotFoundError,
    ProjectCompletionError,
)



@pytest.fixture
def service(project_repo, task_repo, notification):
    return ProjectService(
        project_repo=project_repo,
        task_repo=task_repo,
        notification=notification,
    )
 
 
 
class TestGetProject:
 
    def test_returns_project_when_found(self, service, project_repo, make_project):
        project = make_project()
        project_repo.find_by_id.return_value = project
        result = service.get_project(project.id)
        assert result == project
 
    def test_raises_not_found_when_missing(self, service, project_repo):
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.get_project(uuid4())
 
 
 
class TestGetAllProjects:
 
    def test_returns_all_projects(self, service, project_repo, make_project):
        projects = [make_project(), make_project()]
        project_repo.find_all.return_value = projects
        assert service.get_all_projects() == projects
 
    def test_returns_empty_list_when_none(self, service, project_repo):
        project_repo.find_all.return_value = []
        assert service.get_all_projects() == []
 
 
 
class TestGetProjectTasks:
 
    def test_returns_tasks_for_project(
        self, service, project_repo, task_repo, make_project, make_task
    ):
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
 
    def test_saves_and_returns_project(
        self, service, project_repo, make_project, project_deadline
    ):
        dto = CreateProjectDTO(title="New project", deadline=project_deadline)
        project = make_project(title="New project")
        project_repo.save.return_value = project
        result = service.create_project(dto)
        assert project_repo.save.called
        assert result == project
 
    def test_project_created_with_correct_title(
        self, service, project_repo, project_deadline
    ):
        dto = CreateProjectDTO(title="My project", deadline=project_deadline)
        project_repo.save.side_effect = lambda p: p
        result = service.create_project(dto)
        assert result.title == "My project"
 
    def test_project_created_with_correct_deadline(
        self, service, project_repo, project_deadline
    ):
        dto = CreateProjectDTO(title="My project", deadline=project_deadline)
        project_repo.save.side_effect = lambda p: p
        result = service.create_project(dto)
        assert result.deadline == project_deadline
 
 
 
class TestUpdateProject:
 
    def test_updates_title(self, service, project_repo, task_repo, make_project):
        project = make_project(title="Old")
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        result = service.update_project(project.id, UpdateProjectDTO(title="New"))
        assert result.title == "New"
 
    def test_raises_not_found_if_project_missing(self, service, project_repo):
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.update_project(uuid4(), UpdateProjectDTO(title="New"))
 
    def test_raises_if_no_fields_provided(self, service, project_repo, make_project):
        project = make_project()
        project_repo.find_by_id.return_value = project
        with pytest.raises(InvalidOperationError):
            service.update_project(project.id, UpdateProjectDTO())
 
    def test_notifies_on_earlier_deadline(
        self, service, project_repo, task_repo, notification, make_project, project_deadline
    ):
        project = make_project(deadline=project_deadline)
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        task_repo.find_exceeding_deadline.return_value = []
        earlier = project_deadline - timedelta(days=5)
        service.update_project(project.id, UpdateProjectDTO(deadline=earlier))
        notification.notify.assert_called_once()
        assert isinstance(notification.notify.call_args[0][0], ProjectDeadlineChanged)
 
    def test_cascades_deadline_to_affected_tasks(
        self, service, project_repo, task_repo, notification, make_project, make_task, project_deadline
    ):
        project = make_project(deadline=project_deadline)
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        affected_task = make_task(
            deadline=project_deadline,
            project_id=project.id,
            project_deadline=project_deadline,
        )
        earlier = project_deadline - timedelta(days=5)
        task_repo.find_exceeding_deadline.return_value = [affected_task]
        service.update_project(project.id, UpdateProjectDTO(deadline=earlier))
        task_repo.save.assert_called_once_with(affected_task)
 
    def test_no_cascade_when_deadline_moves_later(
        self, service, project_repo, task_repo, notification, make_project, project_deadline
    ):
        project = make_project(deadline=project_deadline)
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        later = project_deadline + timedelta(days=5)
        service.update_project(project.id, UpdateProjectDTO(deadline=later))
        task_repo.find_exceeding_deadline.assert_not_called()
        notification.notify.assert_not_called()
 

 
class TestDeleteProject:
 
    def test_deletes_project(self, service, project_repo, make_project):
        project = make_project()
        project_repo.find_by_id.return_value = project
        service.delete_project(project.id)
        project_repo.delete.assert_called_once_with(project.id)
 
    def test_raises_not_found_if_project_missing(self, service, project_repo):
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.delete_project(uuid4())
 

 
class TestCompleteProject:
 
    def test_completes_project_with_no_open_tasks(
        self, service, project_repo, task_repo, notification, make_project
    ):
        project = make_project()
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        task_repo.count_open_by_project.return_value = 0
        result = service.complete_project(project.id)
        assert result.completed is True
 
    def test_raises_if_open_tasks_remain(
        self, service, project_repo, task_repo, make_project
    ):
        project = make_project()
        project_repo.find_by_id.return_value = project
        task_repo.count_open_by_project.return_value = 2
        with pytest.raises(ProjectCompletionError):
            service.complete_project(project.id)
 
    def test_notifies_project_completed_event(
        self, service, project_repo, task_repo, notification, make_project
    ):
        project = make_project()
        project_repo.find_by_id.return_value = project
        project_repo.save.side_effect = lambda p: p
        task_repo.count_open_by_project.return_value = 0
        service.complete_project(project.id)
        notification.notify.assert_called_once()
        assert isinstance(notification.notify.call_args[0][0], ProjectCompleted)
 
    def test_raises_not_found_if_project_missing(self, service, project_repo):
        project_repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.complete_project(uuid4())