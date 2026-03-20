"""
API tests for task router.

Uses TestClient with overridden dependencies — no real DB,
services are mocked via FastAPI dependency overrides.
"""

from uuid import uuid4

from src.domain.exceptions.exceptions import (
    DeadlineViolationError,
    InvalidOperationError,
    NotFoundError,
    TaskAlreadyCompletedError,
)


class TestListTasks:
    def test_returns_200(self, api_client, mock_task_service):
        mock_task_service.get_all_tasks.return_value = []
        assert api_client.get("/api/v1/tasks").status_code == 200

    def test_returns_empty_list(self, api_client, mock_task_service):
        mock_task_service.get_all_tasks.return_value = []
        assert api_client.get("/api/v1/tasks").json() == []

    def test_returns_all_tasks(self, api_client, mock_task_service, make_task):
        mock_task_service.get_all_tasks.return_value = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
        ]
        assert len(api_client.get("/api/v1/tasks").json()) == 2

    def test_completed_filter_passed_to_service(self, api_client, mock_task_service):
        mock_task_service.get_all_tasks.return_value = []
        api_client.get("/api/v1/tasks?completed=true")
        mock_task_service.get_all_tasks.assert_called_once()

    def test_overdue_filter_passed_to_service(self, api_client, mock_task_service):
        mock_task_service.get_all_tasks.return_value = []
        api_client.get("/api/v1/tasks?overdue=true")
        mock_task_service.get_all_tasks.assert_called_once()

    def test_project_id_filter_passed_to_service(self, api_client, mock_task_service):
        mock_task_service.get_all_tasks.return_value = []
        api_client.get(f"/api/v1/tasks?project_id={uuid4()}")
        mock_task_service.get_all_tasks.assert_called_once()


class TestGetTask:
    def test_returns_200(self, api_client, mock_task_service, make_task):
        task = make_task()
        mock_task_service.get_task.return_value = task
        assert api_client.get(f"/api/v1/tasks/{task.id}").status_code == 200

    def test_returns_task_data(self, api_client, mock_task_service, make_task):
        task = make_task(title="My task")
        mock_task_service.get_task.return_value = task
        data = api_client.get(f"/api/v1/tasks/{task.id}").json()
        assert data["title"] == "My task"

    def test_not_found_returns_404(self, api_client, mock_task_service):
        mock_task_service.get_task.side_effect = NotFoundError("Task", str(uuid4()))
        assert api_client.get(f"/api/v1/tasks/{uuid4()}").status_code == 404


class TestCreateTask:
    def test_returns_201(self, api_client, mock_task_service, make_task):
        mock_task_service.create_task.return_value = make_task()
        response = api_client.post(
            "/api/v1/tasks",
            json={
                "title": "My task",
                "deadline": "2025-12-01T00:00:00Z",
            },
        )
        assert response.status_code == 201

    def test_returns_task_data(self, api_client, mock_task_service, make_task):
        task = make_task(title="My task")
        mock_task_service.create_task.return_value = task
        data = api_client.post(
            "/api/v1/tasks",
            json={
                "title": "My task",
                "deadline": "2025-12-01T00:00:00Z",
            },
        ).json()
        assert data["title"] == "My task"
        assert "id" in data
        assert data["completed"] is False

    def test_missing_title_returns_422(self, api_client):
        response = api_client.post(
            "/api/v1/tasks",
            json={
                "deadline": "2025-12-01T00:00:00Z",
            },
        )
        assert response.status_code == 422

    def test_missing_deadline_returns_422(self, api_client):
        response = api_client.post(
            "/api/v1/tasks",
            json={
                "title": "My task",
            },
        )
        assert response.status_code == 422

    def test_empty_title_returns_422(self, api_client):
        response = api_client.post(
            "/api/v1/tasks",
            json={
                "title": "",
                "deadline": "2025-12-01T00:00:00Z",
            },
        )
        assert response.status_code == 422

    def test_deadline_violation_returns_422(self, api_client, mock_task_service):
        mock_task_service.create_task.side_effect = DeadlineViolationError("Exceeded.")
        response = api_client.post(
            "/api/v1/tasks",
            json={
                "title": "My task",
                "deadline": "2025-12-01T00:00:00Z",
            },
        )
        assert response.status_code == 422

    def test_project_not_found_returns_404(self, api_client, mock_task_service):
        mock_task_service.create_task.side_effect = NotFoundError(
            "Project", str(uuid4())
        )
        response = api_client.post(
            "/api/v1/tasks",
            json={
                "title": "My task",
                "deadline": "2025-12-01T00:00:00Z",
                "project_id": str(uuid4()),
            },
        )
        assert response.status_code == 404


class TestUpdateTask:
    def test_returns_200(self, api_client, mock_task_service, make_task):
        task = make_task(title="New title")
        mock_task_service.update_task.return_value = task
        response = api_client.put(
            f"/api/v1/tasks/{task.id}",
            json={
                "title": "New title",
            },
        )
        assert response.status_code == 200

    def test_returns_updated_task(self, api_client, mock_task_service, make_task):
        task = make_task(title="New title")
        mock_task_service.update_task.return_value = task
        data = api_client.put(
            f"/api/v1/tasks/{task.id}",
            json={
                "title": "New title",
            },
        ).json()
        assert data["title"] == "New title"

    def test_not_found_returns_404(self, api_client, mock_task_service):
        mock_task_service.update_task.side_effect = NotFoundError("Task", str(uuid4()))
        assert (
            api_client.put(
                f"/api/v1/tasks/{uuid4()}", json={"title": "New"}
            ).status_code
            == 404
        )

    def test_no_fields_returns_422(self, api_client):
        assert api_client.put(f"/api/v1/tasks/{uuid4()}", json={}).status_code == 422

    def test_deadline_violation_returns_422(self, api_client, mock_task_service):
        mock_task_service.update_task.side_effect = DeadlineViolationError("Exceeded.")
        assert (
            api_client.put(
                f"/api/v1/tasks/{uuid4()}", json={"title": "New"}
            ).status_code
            == 422
        )

    def test_invalid_operation_returns_409(self, api_client, mock_task_service):
        mock_task_service.update_task.side_effect = InvalidOperationError("Invalid.")
        assert (
            api_client.put(
                f"/api/v1/tasks/{uuid4()}", json={"title": "New"}
            ).status_code
            == 409
        )


class TestDeleteTask:
    def test_returns_204(self, api_client, mock_task_service):
        mock_task_service.delete_task.return_value = None
        assert api_client.delete(f"/api/v1/tasks/{uuid4()}").status_code == 204

    def test_not_found_returns_404(self, api_client, mock_task_service):
        mock_task_service.delete_task.side_effect = NotFoundError("Task", str(uuid4()))
        assert api_client.delete(f"/api/v1/tasks/{uuid4()}").status_code == 404


class TestCompleteTask:
    def test_returns_200(self, api_client, mock_task_service, make_completed_task):
        mock_task_service.complete_task.return_value = make_completed_task()
        assert api_client.patch(f"/api/v1/tasks/{uuid4()}/complete").status_code == 200

    def test_returns_completed_true(
        self, api_client, mock_task_service, make_completed_task
    ):
        mock_task_service.complete_task.return_value = make_completed_task()
        data = api_client.patch(f"/api/v1/tasks/{uuid4()}/complete").json()
        assert data["completed"] is True

    def test_not_found_returns_404(self, api_client, mock_task_service):
        mock_task_service.complete_task.side_effect = NotFoundError(
            "Task", str(uuid4())
        )
        assert api_client.patch(f"/api/v1/tasks/{uuid4()}/complete").status_code == 404

    def test_already_completed_returns_409(self, api_client, mock_task_service):
        mock_task_service.complete_task.side_effect = TaskAlreadyCompletedError(
            "Already done."
        )
        assert api_client.patch(f"/api/v1/tasks/{uuid4()}/complete").status_code == 409
