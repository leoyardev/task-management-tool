"""
Unit tests for dependency injection functions.

Verifies each factory returns the correct service type
with correctly wired dependencies.
"""

from config import AppConfig
from src.adapters.api.dependencies import (
    get_config,
    get_project_service,
    get_task_service,
)
from src.adapters.notification.console_notifier import ConsoleNotificationService
from src.adapters.persistence.repositories.project import SqlProjectRepository
from src.adapters.persistence.repositories.task import SqlTaskRepository
from src.application.project_service import ProjectService
from src.application.task_service import TaskService


class TestGetConfig:
    def test_returns_app_config_instance(self):
        config = get_config()
        assert isinstance(config, AppConfig)

    def test_returns_same_instance_on_multiple_calls(self):
        """lru_cache — same object returned every time."""
        assert get_config() is get_config()


class TestGetProjectService:
    def test_returns_project_service_instance(self, mock_session):
        service = get_project_service(session=mock_session)
        assert isinstance(service, ProjectService)

    def test_project_repo_is_sql_project_repository(self, mock_session):
        service = get_project_service(session=mock_session)
        assert isinstance(service._project_repo, SqlProjectRepository)

    def test_task_repo_is_sql_task_repository(self, mock_session):
        service = get_project_service(session=mock_session)
        assert isinstance(service._task_repo, SqlTaskRepository)

    def test_notification_is_console_notifier(self, mock_session):
        service = get_project_service(session=mock_session)
        assert isinstance(service._notification, ConsoleNotificationService)


class TestGetTaskService:
    def test_returns_task_service_instance(self, mock_session, config):
        service = get_task_service(session=mock_session, config=config)
        assert isinstance(service, TaskService)

    def test_task_repo_is_sql_task_repository(self, mock_session, config):
        service = get_task_service(session=mock_session, config=config)
        assert isinstance(service._task_repo, SqlTaskRepository)

    def test_project_repo_is_sql_project_repository(self, mock_session, config):
        service = get_task_service(session=mock_session, config=config)
        assert isinstance(service._project_repo, SqlProjectRepository)

    def test_notification_is_console_notifier(self, mock_session, config):
        service = get_task_service(session=mock_session, config=config)
        assert isinstance(service._notification, ConsoleNotificationService)

    def test_auto_complete_project_passed_from_config(self, mock_session, monkeypatch):
        monkeypatch.setenv("AUTO_COMPLETE_PROJECT", "true")
        config = AppConfig()
        service = get_task_service(session=mock_session, config=config)
        assert service._auto_complete_project is True

    def test_auto_complete_project_false_by_default(self, mock_session, monkeypatch):
        monkeypatch.setenv("AUTO_COMPLETE_PROJECT", "false")
        config = AppConfig()
        service = get_task_service(session=mock_session, config=config)
        assert service._auto_complete_project is False
