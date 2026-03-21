"""
End-to-end tests for task endpoints.
"""

from datetime import UTC, datetime, timedelta

NOW = datetime.now(UTC)
PROJECT_DEADLINE = (NOW + timedelta(days=30)).isoformat()
TASK_DEADLINE = (NOW + timedelta(days=15)).isoformat()
EARLIER_DEADLINE = (NOW + timedelta(days=7)).isoformat()


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


class TestCreateTask:
    def test_creates_task_and_returns_201(self, e2e_client):
        response = e2e_client.post(
            "/api/v1/tasks",
            json={
                "title": "Write tests",
                "deadline": TASK_DEADLINE,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Write tests"
        assert data["completed"] is False
        assert data["project_id"] is None
        assert "id" in data

    def test_creates_task_with_description(self, e2e_client):
        response = e2e_client.post(
            "/api/v1/tasks",
            json={
                "title": "Write tests",
                "deadline": TASK_DEADLINE,
                "description": "Cover all edge cases",
            },
        )
        assert response.json()["description"] == "Cover all edge cases"

    def test_missing_title_returns_422(self, e2e_client):
        assert (
            e2e_client.post(
                "/api/v1/tasks",
                json={
                    "deadline": TASK_DEADLINE,
                },
            ).status_code
            == 422
        )

    def test_missing_deadline_returns_422(self, e2e_client):
        assert (
            e2e_client.post(
                "/api/v1/tasks",
                json={
                    "title": "My task",
                },
            ).status_code
            == 422
        )

    def test_task_deadline_exceeding_project_deadline_returns_422(self, e2e_client):
        project = create_project(e2e_client)
        response = e2e_client.post(
            "/api/v1/tasks",
            json={
                "title": "Late task",
                "deadline": (NOW + timedelta(days=60)).isoformat(),
                "project_id": project["id"],
            },
        )
        assert response.status_code == 422


class TestListTasks:
    def test_returns_empty_list_initially(self, e2e_client):
        response = e2e_client.get("/api/v1/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_all_tasks(self, e2e_client):
        create_task(e2e_client, "Task 1")
        create_task(e2e_client, "Task 2")
        assert len(e2e_client.get("/api/v1/tasks").json()) == 2

    def test_filter_completed_true(self, e2e_client):
        task = create_task(e2e_client)
        e2e_client.patch(f"/api/v1/tasks/{task['id']}/complete")
        create_task(e2e_client, "Open task")

        results = e2e_client.get("/api/v1/tasks?completed=true").json()
        assert all(t["completed"] for t in results)

    def test_filter_completed_false(self, e2e_client):
        task = create_task(e2e_client)
        e2e_client.patch(f"/api/v1/tasks/{task['id']}/complete")
        create_task(e2e_client, "Open task")

        results = e2e_client.get("/api/v1/tasks?completed=false").json()
        assert all(not t["completed"] for t in results)

    def test_filter_by_project_id(self, e2e_client):
        project = create_project(e2e_client)
        task = create_task(e2e_client)
        e2e_client.post(f"/api/v1/projects/{project['id']}/tasks/{task['id']}/link")
        create_task(e2e_client, "Unlinked task")

        results = e2e_client.get(f"/api/v1/tasks?project_id={project['id']}").json()
        assert len(results) == 1
        assert results[0]["id"] == task["id"]


class TestGetTask:
    def test_returns_task_by_id(self, e2e_client):
        task = create_task(e2e_client, "My task")
        response = e2e_client.get(f"/api/v1/tasks/{task['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == task["id"]

    def test_nonexistent_task_returns_404(self, e2e_client):
        import uuid

        assert e2e_client.get(f"/api/v1/tasks/{uuid.uuid4()}").status_code == 404


class TestUpdateTask:
    def test_updates_title(self, e2e_client):
        task = create_task(e2e_client, "Old title")
        response = e2e_client.put(
            f"/api/v1/tasks/{task['id']}",
            json={
                "title": "New title",
            },
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New title"

    def test_updates_description(self, e2e_client):
        task = create_task(e2e_client)
        response = e2e_client.put(
            f"/api/v1/tasks/{task['id']}",
            json={
                "description": "New description",
            },
        )
        assert response.json()["description"] == "New description"

    def test_no_fields_returns_422(self, e2e_client):
        task = create_task(e2e_client)
        assert e2e_client.put(f"/api/v1/tasks/{task['id']}", json={}).status_code == 422

    def test_deadline_exceeding_project_returns_422(self, e2e_client):
        project = create_project(e2e_client)
        task = create_task(e2e_client)
        e2e_client.post(f"/api/v1/projects/{project['id']}/tasks/{task['id']}/link")

        response = e2e_client.put(
            f"/api/v1/tasks/{task['id']}",
            json={
                "deadline": (NOW + timedelta(days=60)).isoformat(),
            },
        )
        assert response.status_code == 422

    def test_nonexistent_task_returns_404(self, e2e_client):
        import uuid

        assert (
            e2e_client.put(
                f"/api/v1/tasks/{uuid.uuid4()}",
                json={"title": "New"},
            ).status_code
            == 404
        )


class TestDeleteTask:
    def test_deletes_task(self, e2e_client):
        task = create_task(e2e_client)
        assert e2e_client.delete(f"/api/v1/tasks/{task['id']}").status_code == 204
        assert e2e_client.get(f"/api/v1/tasks/{task['id']}").status_code == 404

    def test_nonexistent_task_returns_404(self, e2e_client):
        import uuid

        assert e2e_client.delete(f"/api/v1/tasks/{uuid.uuid4()}").status_code == 404


class TestCompleteTask:
    def test_completes_task(self, e2e_client):
        task = create_task(e2e_client)
        response = e2e_client.patch(f"/api/v1/tasks/{task['id']}/complete")
        assert response.status_code == 200
        assert response.json()["completed"] is True

    def test_already_completed_returns_409(self, e2e_client):
        task = create_task(e2e_client)
        e2e_client.patch(f"/api/v1/tasks/{task['id']}/complete")
        assert (
            e2e_client.patch(f"/api/v1/tasks/{task['id']}/complete").status_code == 409
        )

    def test_nonexistent_task_returns_404(self, e2e_client):
        import uuid

        assert (
            e2e_client.patch(f"/api/v1/tasks/{uuid.uuid4()}/complete").status_code
            == 404
        )


class TestLinkUnlink:
    def test_links_task_to_project(self, e2e_client):
        project = create_project(e2e_client)
        task = create_task(e2e_client)

        response = e2e_client.post(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}/link"
        )
        assert response.status_code == 200
        assert response.json()["project_id"] == project["id"]

    def test_unlinks_task_from_project(self, e2e_client):
        project = create_project(e2e_client)
        task = create_task(e2e_client)
        e2e_client.post(f"/api/v1/projects/{project['id']}/tasks/{task['id']}/link")

        response = e2e_client.delete(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}/unlink"
        )
        assert response.status_code == 200
        assert response.json()["project_id"] is None

    def test_task_deadline_cannot_exceed_project_on_link(self, e2e_client):
        project = create_project(e2e_client)
        task = create_task(e2e_client, deadline=(NOW + timedelta(days=60)).isoformat())

        response = e2e_client.post(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}/link"
        )
        assert response.status_code == 422


class TestTaskLifecycle:
    def test_create_link_complete_reopen_unlink_delete(self, e2e_client):
        project = create_project(e2e_client)
        task = create_task(e2e_client)
        task_id = task["id"]
        project_id = project["id"]

        # link
        linked = e2e_client.post(
            f"/api/v1/projects/{project_id}/tasks/{task_id}/link"
        ).json()
        assert linked["project_id"] == project_id

        # complete
        completed = e2e_client.patch(f"/api/v1/tasks/{task_id}/complete").json()
        assert completed["completed"] is True

        # unlink
        unlinked = e2e_client.delete(
            f"/api/v1/projects/{project_id}/tasks/{task_id}/unlink"
        ).json()
        assert unlinked["project_id"] is None

        # delete
        assert e2e_client.delete(f"/api/v1/tasks/{task_id}").status_code == 204
        assert e2e_client.get(f"/api/v1/tasks/{task_id}").status_code == 404


class TestDeadlineConstraint:
    def test_project_deadline_cascades_to_tasks(self, e2e_client):
        """
        When project deadline moves earlier, tasks exceeding it
        are automatically adjusted.
        """
        project = create_project(
            e2e_client, deadline=(NOW + timedelta(days=30)).isoformat()
        )
        task = create_task(e2e_client, deadline=(NOW + timedelta(days=20)).isoformat())
        e2e_client.post(f"/api/v1/projects/{project['id']}/tasks/{task['id']}/link")

        # move project deadline earlier than task deadline
        e2e_client.put(
            f"/api/v1/projects/{project['id']}",
            json={
                "deadline": (NOW + timedelta(days=10)).isoformat(),
            },
        )

        # task deadline should have been cascaded
        updated_task = e2e_client.get(f"/api/v1/tasks/{task['id']}").json()
        task_deadline = datetime.fromisoformat(
            updated_task["deadline"].replace("Z", "+00:00")
        )
        project_deadline = NOW + timedelta(days=10)
        assert task_deadline <= project_deadline

    def test_completing_project_requires_all_tasks_done(self, e2e_client):
        project = create_project(e2e_client)
        task = create_task(e2e_client)
        e2e_client.post(f"/api/v1/projects/{project['id']}/tasks/{task['id']}/link")

        # cannot complete with open task
        assert (
            e2e_client.patch(f"/api/v1/projects/{project['id']}/complete").status_code
            == 422
        )

        # complete task first
        e2e_client.patch(f"/api/v1/tasks/{task['id']}/complete")

        # now project can complete
        assert (
            e2e_client.patch(f"/api/v1/projects/{project['id']}/complete").status_code
            == 200
        )
