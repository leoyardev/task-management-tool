"""
API tests for project router.

Uses TestClient with overridden dependencies — no real DB,
services are mocked via FastAPI dependency overrides.
"""

from uuid import uuid4

from src.domain.exceptions.exceptions import (
    InvalidOperationError,
    NotFoundError,
    ProjectCompletionError,
)


class TestCreateProject:
    def test_returns_201(self, api_client, mock_project_service, make_project):
        mock_project_service.create_project.return_value = make_project()
        response = api_client.post(
            "/api/v1/projects",
            json={
                "title": "My project",
                "deadline": "2025-12-01T00:00:00Z",
            },
        )
        assert response.status_code == 201

    def test_returns_project_data(self, api_client, mock_project_service, make_project):
        project = make_project(title="My project")
        mock_project_service.create_project.return_value = project
        data = api_client.post(
            "/api/v1/projects",
            json={
                "title": "My project",
                "deadline": "2025-12-01T00:00:00Z",
            },
        ).json()
        assert data["title"] == "My project"
        assert "id" in data
        assert data["completed"] is False

    def test_missing_title_returns_422(self, api_client):
        response = api_client.post(
            "/api/v1/projects",
            json={
                "deadline": "2025-12-01T00:00:00Z",
            },
        )
        assert response.status_code == 422

    def test_missing_deadline_returns_422(self, api_client):
        response = api_client.post(
            "/api/v1/projects",
            json={
                "title": "My project",
            },
        )
        assert response.status_code == 422

    def test_empty_title_returns_422(self, api_client):
        response = api_client.post(
            "/api/v1/projects",
            json={
                "title": "",
                "deadline": "2025-12-01T00:00:00Z",
            },
        )
        assert response.status_code == 422


class TestListProjects:
    def test_returns_200(self, api_client, mock_project_service):
        mock_project_service.get_all_projects.return_value = []
        assert api_client.get("/api/v1/projects").status_code == 200

    def test_returns_empty_list(self, api_client, mock_project_service):
        mock_project_service.get_all_projects.return_value = []
        assert api_client.get("/api/v1/projects").json() == []

    def test_returns_all_projects(self, api_client, mock_project_service, make_project):
        mock_project_service.get_all_projects.return_value = [
            make_project(title="P1"),
            make_project(title="P2"),
        ]
        assert len(api_client.get("/api/v1/projects").json()) == 2


class TestGetProject:
    def test_returns_200(self, api_client, mock_project_service, make_project):
        project = make_project()
        mock_project_service.get_project.return_value = project
        assert api_client.get(f"/api/v1/projects/{project.id}").status_code == 200

    def test_returns_project_data(self, api_client, mock_project_service, make_project):
        project = make_project(title="My project")
        mock_project_service.get_project.return_value = project
        data = api_client.get(f"/api/v1/projects/{project.id}").json()
        assert data["title"] == "My project"

    def test_not_found_returns_404(self, api_client, mock_project_service):
        mock_project_service.get_project.side_effect = NotFoundError(
            "Project", str(uuid4())
        )
        assert api_client.get(f"/api/v1/projects/{uuid4()}").status_code == 404


class TestUpdateProject:
    def test_returns_200(self, api_client, mock_project_service, make_project):
        project = make_project(title="New title")
        mock_project_service.update_project.return_value = project
        response = api_client.put(
            f"/api/v1/projects/{project.id}",
            json={
                "title": "New title",
            },
        )
        assert response.status_code == 200

    def test_returns_updated_project(
        self, api_client, mock_project_service, make_project
    ):
        project = make_project(title="New title")
        mock_project_service.update_project.return_value = project
        data = api_client.put(
            f"/api/v1/projects/{project.id}",
            json={
                "title": "New title",
            },
        ).json()
        assert data["title"] == "New title"

    def test_not_found_returns_404(self, api_client, mock_project_service):
        mock_project_service.update_project.side_effect = NotFoundError(
            "Project", str(uuid4())
        )
        assert (
            api_client.put(
                f"/api/v1/projects/{uuid4()}", json={"title": "New"}
            ).status_code
            == 404
        )

    def test_no_fields_returns_422(self, api_client):
        assert api_client.put(f"/api/v1/projects/{uuid4()}", json={}).status_code == 422

    def test_invalid_operation_returns_409(self, api_client, mock_project_service):
        mock_project_service.update_project.side_effect = InvalidOperationError(
            "Invalid."
        )
        assert (
            api_client.put(
                f"/api/v1/projects/{uuid4()}", json={"title": "New"}
            ).status_code
            == 409
        )


class TestDeleteProject:
    def test_returns_204(self, api_client, mock_project_service, make_project):
        mock_project_service.delete_project.return_value = None
        assert api_client.delete(f"/api/v1/projects/{uuid4()}").status_code == 204

    def test_not_found_returns_404(self, api_client, mock_project_service):
        mock_project_service.delete_project.side_effect = NotFoundError(
            "Project", str(uuid4())
        )
        assert api_client.delete(f"/api/v1/projects/{uuid4()}").status_code == 404


class TestCompleteProject:
    def test_returns_200(self, api_client, mock_project_service, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        mock_project_service.complete_project.return_value = project
        assert (
            api_client.patch(f"/api/v1/projects/{project.id}/complete").status_code
            == 200
        )

    def test_returns_completed_true(
        self, api_client, mock_project_service, make_project
    ):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        mock_project_service.complete_project.return_value = project
        data = api_client.patch(f"/api/v1/projects/{project.id}/complete").json()
        assert data["completed"] is True

    def test_open_tasks_returns_422(self, api_client, mock_project_service):
        mock_project_service.complete_project.side_effect = ProjectCompletionError(
            "Tasks open."
        )
        assert (
            api_client.patch(f"/api/v1/projects/{uuid4()}/complete").status_code == 422
        )

    def test_not_found_returns_404(self, api_client, mock_project_service):
        mock_project_service.complete_project.side_effect = NotFoundError(
            "Project", str(uuid4())
        )
        assert (
            api_client.patch(f"/api/v1/projects/{uuid4()}/complete").status_code == 404
        )


class TestGetProjectTasks:
    def test_returns_200(self, api_client, mock_project_service):
        mock_project_service.get_project_tasks.return_value = []
        assert api_client.get(f"/api/v1/projects/{uuid4()}/tasks").status_code == 200

    def test_returns_tasks_for_project(
        self, api_client, mock_project_service, make_task
    ):
        mock_project_service.get_project_tasks.return_value = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
        ]
        assert len(api_client.get(f"/api/v1/projects/{uuid4()}/tasks").json()) == 2

    def test_not_found_returns_404(self, api_client, mock_project_service):
        mock_project_service.get_project_tasks.side_effect = NotFoundError(
            "Project", str(uuid4())
        )
        assert api_client.get(f"/api/v1/projects/{uuid4()}/tasks").status_code == 404


class TestLinkTask:
    def test_returns_200(self, api_client, mock_task_service, make_task):
        mock_task_service.link_to_project.return_value = make_task()
        assert (
            api_client.post(
                f"/api/v1/projects/{uuid4()}/tasks/{uuid4()}/link"
            ).status_code
            == 200
        )

    def test_not_found_returns_404(self, api_client, mock_task_service):
        mock_task_service.link_to_project.side_effect = NotFoundError(
            "Task", str(uuid4())
        )
        assert (
            api_client.post(
                f"/api/v1/projects/{uuid4()}/tasks/{uuid4()}/link"
            ).status_code
            == 404
        )


class TestUnlinkTask:
    def test_returns_200(self, api_client, mock_task_service, make_task):
        mock_task_service.unlink_from_project.return_value = make_task()
        assert (
            api_client.delete(
                f"/api/v1/projects/{uuid4()}/tasks/{uuid4()}/unlink"
            ).status_code
            == 200
        )

    def test_not_found_returns_404(self, api_client, mock_task_service):
        mock_task_service.unlink_from_project.side_effect = NotFoundError(
            "Task", str(uuid4())
        )
        assert (
            api_client.delete(
                f"/api/v1/projects/{uuid4()}/tasks/{uuid4()}/unlink"
            ).status_code
            == 404
        )
