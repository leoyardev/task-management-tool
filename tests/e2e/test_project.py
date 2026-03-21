"""
End-to-end tests for project endpoints.
"""

from datetime import UTC, datetime, timedelta

NOW = datetime.now(UTC)
DEADLINE = (NOW + timedelta(days=30)).isoformat()
EARLIER_DEADLINE = (NOW + timedelta(days=15)).isoformat()


class TestCreateProject:
    def test_creates_project_and_returns_201(self, e2e_client):
        response = e2e_client.post(
            "/api/v1/projects",
            json={
                "title": "Launch app",
                "deadline": DEADLINE,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Launch app"
        assert data["completed"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_missing_title_returns_422(self, e2e_client):
        assert (
            e2e_client.post(
                "/api/v1/projects",
                json={
                    "deadline": DEADLINE,
                },
            ).status_code
            == 422
        )

    def test_missing_deadline_returns_422(self, e2e_client):
        assert (
            e2e_client.post(
                "/api/v1/projects",
                json={
                    "title": "My project",
                },
            ).status_code
            == 422
        )


class TestListProjects:
    def test_returns_empty_list_initially(self, e2e_client):
        response = e2e_client.get("/api/v1/projects")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_created_projects(self, e2e_client):
        e2e_client.post("/api/v1/projects", json={"title": "P1", "deadline": DEADLINE})
        e2e_client.post("/api/v1/projects", json={"title": "P2", "deadline": DEADLINE})
        response = e2e_client.get("/api/v1/projects")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestGetProject:
    def test_returns_project_by_id(self, e2e_client):
        project_id = e2e_client.post(
            "/api/v1/projects",
            json={
                "title": "My project",
                "deadline": DEADLINE,
            },
        ).json()["id"]

        response = e2e_client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["id"] == project_id

    def test_nonexistent_project_returns_404(self, e2e_client):
        import uuid

        assert e2e_client.get(f"/api/v1/projects/{uuid.uuid4()}").status_code == 404


class TestUpdateProject:
    def test_updates_title(self, e2e_client):
        project_id = e2e_client.post(
            "/api/v1/projects",
            json={
                "title": "Old title",
                "deadline": DEADLINE,
            },
        ).json()["id"]

        response = e2e_client.put(
            f"/api/v1/projects/{project_id}",
            json={
                "title": "New title",
            },
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New title"

    def test_updates_deadline(self, e2e_client):
        project_id = e2e_client.post(
            "/api/v1/projects",
            json={
                "title": "My project",
                "deadline": DEADLINE,
            },
        ).json()["id"]

        response = e2e_client.put(
            f"/api/v1/projects/{project_id}",
            json={
                "deadline": EARLIER_DEADLINE,
            },
        )
        assert response.status_code == 200

    def test_no_fields_returns_422(self, e2e_client):
        project_id = e2e_client.post(
            "/api/v1/projects",
            json={
                "title": "My project",
                "deadline": DEADLINE,
            },
        ).json()["id"]

        assert (
            e2e_client.put(f"/api/v1/projects/{project_id}", json={}).status_code == 422
        )

    def test_nonexistent_project_returns_404(self, e2e_client):
        import uuid

        assert (
            e2e_client.put(
                f"/api/v1/projects/{uuid.uuid4()}",
                json={"title": "New"},
            ).status_code
            == 404
        )


class TestDeleteProject:
    def test_deletes_project(self, e2e_client):
        project_id = e2e_client.post(
            "/api/v1/projects",
            json={
                "title": "Delete me",
                "deadline": DEADLINE,
            },
        ).json()["id"]

        assert e2e_client.delete(f"/api/v1/projects/{project_id}").status_code == 204
        assert e2e_client.get(f"/api/v1/projects/{project_id}").status_code == 404

    def test_nonexistent_project_returns_404(self, e2e_client):
        import uuid

        assert e2e_client.delete(f"/api/v1/projects/{uuid.uuid4()}").status_code == 404


class TestCompleteProject:
    def test_completes_project_with_no_tasks(self, e2e_client):
        project_id = e2e_client.post(
            "/api/v1/projects",
            json={
                "title": "Done project",
                "deadline": DEADLINE,
            },
        ).json()["id"]

        response = e2e_client.patch(f"/api/v1/projects/{project_id}/complete")
        assert response.status_code == 200
        assert response.json()["completed"] is True

    def test_cannot_complete_with_open_tasks(self, e2e_client):
        project_id = e2e_client.post(
            "/api/v1/projects",
            json={
                "title": "Has tasks",
                "deadline": DEADLINE,
            },
        ).json()["id"]

        task_id = e2e_client.post(
            "/api/v1/tasks",
            json={
                "title": "Open task",
                "deadline": EARLIER_DEADLINE,
            },
        ).json()["id"]

        e2e_client.post(f"/api/v1/projects/{project_id}/tasks/{task_id}/link")

        assert (
            e2e_client.patch(f"/api/v1/projects/{project_id}/complete").status_code
            == 422
        )


class TestProjectLifecycle:
    def test_create_update_complete_delete(self, e2e_client):
        # create
        project = e2e_client.post(
            "/api/v1/projects",
            json={
                "title": "My project",
                "deadline": DEADLINE,
            },
        ).json()
        project_id = project["id"]
        assert project["completed"] is False

        # update
        updated = e2e_client.put(
            f"/api/v1/projects/{project_id}",
            json={
                "title": "Updated project",
            },
        ).json()
        assert updated["title"] == "Updated project"

        # complete
        completed = e2e_client.patch(f"/api/v1/projects/{project_id}/complete").json()
        assert completed["completed"] is True

        # delete
        assert e2e_client.delete(f"/api/v1/projects/{project_id}").status_code == 204
        assert e2e_client.get(f"/api/v1/projects/{project_id}").status_code == 404
