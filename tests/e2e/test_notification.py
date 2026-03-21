"""
End-to-end tests verifying ConsoleNotificationService logs
are emitted when domain events are triggered via the API.
"""

from datetime import UTC, datetime, timedelta

import pytest

NOW = datetime.now(UTC)
PROJECT_DEADLINE = (NOW + timedelta(days=30)).isoformat()
TASK_DEADLINE = (NOW + timedelta(days=15)).isoformat()


def create_project(client, title="Test project", deadline=None) -> dict:
    return client.post(
        "/api/v1/projects",
        json={
            "title": title,
            "deadline": deadline or PROJECT_DEADLINE,
        },
    ).json()


def create_task(client, title="Test task", deadline=None) -> dict:
    return client.post(
        "/api/v1/tasks",
        json={
            "title": title,
            "deadline": deadline or TASK_DEADLINE,
        },
    ).json()


class TestTaskCompletedNotification:
    def test_completing_task_logs_info(self, e2e_client, caplog):
        task = create_task(e2e_client, title="Write docs")

        with caplog.at_level("INFO"):
            e2e_client.patch(f"/api/v1/tasks/{task['id']}/complete")

        assert any(
            "Task completed" in record.message and record.levelname == "INFO"
            for record in caplog.records
        )

    def test_completed_log_contains_task_id(self, e2e_client, caplog):
        task = create_task(e2e_client)

        with caplog.at_level("INFO"):
            e2e_client.patch(f"/api/v1/tasks/{task['id']}/complete")

        assert any(task["id"] in record.message for record in caplog.records)

    def test_completed_log_contains_task_title(self, e2e_client, caplog):
        task = create_task(e2e_client, title="My specific task")

        with caplog.at_level("INFO"):
            e2e_client.patch(f"/api/v1/tasks/{task['id']}/complete")

        assert any("My specific task" in record.message for record in caplog.records)


class TestProjectCompletedNotification:
    def test_completing_project_logs_info(self, e2e_client, caplog):
        project = create_project(e2e_client)

        with caplog.at_level("INFO"):
            e2e_client.patch(f"/api/v1/projects/{project['id']}/complete")

        assert any(
            "Project completed" in record.message and record.levelname == "INFO"
            for record in caplog.records
        )

    def test_completed_log_contains_project_id(self, e2e_client, caplog):
        project = create_project(e2e_client)

        with caplog.at_level("INFO"):
            e2e_client.patch(f"/api/v1/projects/{project['id']}/complete")

        assert any(project["id"] in record.message for record in caplog.records)


class TestProjectDeadlineChangedNotification:
    def test_earlier_deadline_logs_warning(self, e2e_client, caplog):
        project = create_project(e2e_client)
        earlier = (NOW + timedelta(days=10)).isoformat()

        with caplog.at_level("WARNING"):
            e2e_client.put(
                f"/api/v1/projects/{project['id']}",
                json={
                    "deadline": earlier,
                },
            )

        assert any(
            "Project deadline changed" in record.message
            and record.levelname == "WARNING"
            for record in caplog.records
        )

    def test_deadline_changed_log_contains_project_id(self, e2e_client, caplog):
        project = create_project(e2e_client)
        earlier = (NOW + timedelta(days=10)).isoformat()

        with caplog.at_level("WARNING"):
            e2e_client.put(
                f"/api/v1/projects/{project['id']}",
                json={
                    "deadline": earlier,
                },
            )

        assert any(project["id"] in record.message for record in caplog.records)

    def test_later_deadline_does_not_log_warning(self, e2e_client, caplog):
        project = create_project(e2e_client)
        later = (NOW + timedelta(days=60)).isoformat()

        with caplog.at_level("WARNING"):
            e2e_client.put(
                f"/api/v1/projects/{project['id']}",
                json={
                    "deadline": later,
                },
            )

        assert not any(
            "Project deadline changed" in record.message for record in caplog.records
        )


class TestAutoCompleteProjectNotification:
    @pytest.fixture
    def auto_complete_client(self):
        """
        e2e client with AUTO_COMPLETE_PROJECT=true.
        Completing the last open task should also complete the project.
        """
        from fastapi.testclient import TestClient

        from main import create_app
        from src.adapters.api.dependencies import get_db, get_task_service
        from src.adapters.notification.console_notifier import (
            ConsoleNotificationService,
        )
        from src.adapters.persistence.repositories.project import SqlProjectRepository
        from src.adapters.persistence.repositories.task import SqlTaskRepository
        from src.application.task_service import TaskService
        from src.infrastructure.database import (
            Base,
            build_engine,
            build_session_factory,
        )

        engine = build_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        factory = build_session_factory(engine)

        session = factory()
        session.begin_nested()

        def override_get_db():
            yield session

        def override_get_task_service():
            return TaskService(
                task_repo=SqlTaskRepository(session),
                project_repo=SqlProjectRepository(session),
                notification=ConsoleNotificationService(),
                auto_complete_project=True,  # ← enabled
            )

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_task_service] = override_get_task_service

        client = TestClient(app, raise_server_exceptions=True)
        yield client

        session.rollback()
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()

    def test_completing_last_task_logs_project_completed(
        self, auto_complete_client, caplog
    ):
        project = auto_complete_client.post(
            "/api/v1/projects",
            json={
                "title": "Auto project",
                "deadline": PROJECT_DEADLINE,
            },
        ).json()

        task = auto_complete_client.post(
            "/api/v1/tasks",
            json={
                "title": "Only task",
                "deadline": TASK_DEADLINE,
            },
        ).json()

        auto_complete_client.post(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}/link"
        )

        with caplog.at_level("INFO"):
            auto_complete_client.patch(f"/api/v1/tasks/{task['id']}/complete")

        messages = [r.message for r in caplog.records]
        assert any("Task completed" in m for m in messages)
        assert any("Project completed" in m for m in messages)
