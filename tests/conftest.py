"""
Shared fixtures and helpers across all test modules.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, create_autospec
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import create_app
from src.adapters.api.dependencies import get_project_service, get_task_service
from src.adapters.notification.console_notifier import ConsoleNotificationService
from src.adapters.persistence.models import ProjectDBModel, TaskDBModel
from src.adapters.persistence.repositories.project import SqlProjectRepository
from src.adapters.persistence.repositories.task import SqlTaskRepository
from src.application.project_service import ProjectService
from src.application.task_service import TaskService
from src.domain.entities.project import Project
from src.domain.entities.task import Task
from src.domain.ports.notification import NotificationPort
from src.domain.ports.project import ProjectRepository
from src.domain.ports.task import TaskRepository
from src.infrastructure.database import Base, build_engine, build_session_factory

NOW = datetime.now(UTC)
PROJECT_DEADLINE = NOW + timedelta(days=30)
PROJECT_ID = uuid4()
TASK_ID = uuid4()
TASK_TITLE = "Test task"


@pytest.fixture
def task_id():
    return TASK_ID


@pytest.fixture
def task_title():
    return TASK_TITLE


@pytest.fixture
def now():
    return NOW


@pytest.fixture
def project_deadline():
    return PROJECT_DEADLINE


@pytest.fixture
def project_id():
    return PROJECT_ID


@pytest.fixture
def make_task():
    def _make_task(**kwargs) -> Task:
        return Task.create(
            title=kwargs.pop("title", "Test task"),
            deadline=kwargs.pop("deadline", NOW + timedelta(days=7)),
            **kwargs,
        )

    return _make_task


@pytest.fixture
def make_project():
    def _make_project(**kwargs) -> Project:
        defaults = dict(title="Test project", deadline=PROJECT_DEADLINE)
        return Project.create(**{**defaults, **kwargs})

    return _make_project


@pytest.fixture
def make_linked_task():
    def _make_linked_task(**kwargs) -> Task:
        return Task.create(
            title=kwargs.pop("title", "Linked task"),
            deadline=kwargs.pop("deadline", NOW + timedelta(days=7)),
            project_id=kwargs.pop("project_id", PROJECT_ID),
            project_deadline=kwargs.pop("project_deadline", PROJECT_DEADLINE),
            **kwargs,
        )

    return _make_linked_task


@pytest.fixture
def make_completed_task():
    def _make_completed_task(**kwargs) -> Task:
        task = Task.create(
            title=kwargs.pop("title", "Test task"),
            deadline=kwargs.pop("deadline", NOW + timedelta(days=7)),
            **kwargs,
        )
        task.mark_complete()
        task.pull_events()
        return task

    return _make_completed_task


@pytest.fixture
def make_overdue_task():
    def _make_overdue_task(**kwargs) -> Task:
        return Task.create(
            title=kwargs.pop("title", "Test task"),
            deadline=kwargs.pop("deadline", NOW - timedelta(days=1)),
            **kwargs,
        )

    return _make_overdue_task


@pytest.fixture
def task_repo():
    return create_autospec(TaskRepository)


@pytest.fixture
def project_repo():
    return create_autospec(ProjectRepository)


@pytest.fixture
def notification():
    return create_autospec(NotificationPort)


@pytest.fixture(scope="session")
def engine():
    """
    In-memory SQLite engine shared across the entire test session.
    All ORM models are imported here to register them in Base.metadata
    before create_all() runs.
    """

    _engine = build_engine("sqlite:///:memory:")
    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)
    _engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine):
    """
    Session factory bound to the shared engine.
    Created once per test session.
    """
    return build_session_factory(engine)


@pytest.fixture(scope="function")
def session(session_factory):
    """
    Transactional session per test.

    Uses begin_nested() (savepoint) so each test runs inside
    its own nested transaction that is rolled back on completion.
    Nothing leaks between tests — schema is never recreated.
    """
    _session = session_factory()
    _session.begin_nested()
    yield _session
    _session.rollback()
    _session.close()


@pytest.fixture
def make_project_row():
    def _make_project_row(**kwargs) -> ProjectDBModel:
        defaults = dict(
            id=str(uuid4()),
            title="Test project",
            deadline=datetime.now(UTC) + timedelta(days=30),
        )
        return ProjectDBModel(**{**defaults, **kwargs})

    return _make_project_row


@pytest.fixture
def make_task_row():
    def _make_task_row(**kwargs) -> TaskDBModel:
        defaults = dict(
            id=str(uuid4()),
            title="Test task",
            deadline=datetime.now(UTC) + timedelta(days=7),
        )
        return TaskDBModel(**{**defaults, **kwargs})

    return _make_task_row


@pytest.fixture
def notifier():
    return ConsoleNotificationService()


@pytest.fixture
def config():
    from config import AppConfig

    return AppConfig()


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def project_service(mock_session):
    return ProjectService(
        project_repo=SqlProjectRepository(mock_session),
        task_repo=SqlTaskRepository(mock_session),
        notification=ConsoleNotificationService(),
    )


@pytest.fixture
def task_service(mock_session, config):
    return TaskService(
        task_repo=SqlTaskRepository(mock_session),
        project_repo=SqlProjectRepository(mock_session),
        notification=ConsoleNotificationService(),
        auto_complete_project=config.auto_complete_project,
    )


@pytest.fixture
def mock_project_service():
    return create_autospec(ProjectService)


@pytest.fixture
def mock_task_service():
    return create_autospec(TaskService)


@pytest.fixture
def api_client(mock_project_service, mock_task_service):
    app = create_app()
    app.dependency_overrides[get_project_service] = lambda: mock_project_service
    app.dependency_overrides[get_task_service] = lambda: mock_task_service
    return TestClient(app)
