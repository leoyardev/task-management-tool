"""
Shared fixtures and helpers across all test modules.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec
from uuid import uuid4

import pytest

from src.domain.entities.project import Project
from src.domain.entities.task import Task
from src.domain.ports.notification import NotificationPort
from src.domain.ports.project import ProjectRepository
from src.domain.ports.task import TaskRepository

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
