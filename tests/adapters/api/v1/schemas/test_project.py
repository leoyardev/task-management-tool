"""
Unit tests for v1 project schemas.

Verifies validation rules on ProjectCreate and
"""

from uuid import UUID, uuid4

import pytest

from src.adapters.api.v1.schemas.project import ProjectCreate, ProjectResponse


class TestProjectCreate:
    def test_valid_input_creates_schema(self, now, project_deadline):
        schema = ProjectCreate(title="My project", deadline=project_deadline)
        assert schema.title == "My project"
        assert schema.deadline == project_deadline

    def test_missing_title_raises(self, project_deadline):
        with pytest.raises(Exception):
            ProjectCreate(deadline=project_deadline)

    def test_missing_deadline_raises(self):
        with pytest.raises(Exception):
            ProjectCreate(title="My project")

    def test_empty_title_raises(self, project_deadline):
        with pytest.raises(Exception):
            ProjectCreate(title="", deadline=project_deadline)

    def test_title_exceeding_max_length_raises(self, project_deadline):
        with pytest.raises(Exception):
            ProjectCreate(title="x" * 256, deadline=project_deadline)

    def test_title_at_max_length_is_valid(self, project_deadline):
        schema = ProjectCreate(title="x" * 255, deadline=project_deadline)
        assert len(schema.title) == 255

    def test_title_of_one_character_is_valid(self, project_deadline):
        schema = ProjectCreate(title="x", deadline=project_deadline)
        assert schema.title == "x"


class TestProjectResponse:
    def test_creates_from_fields(self, now, project_deadline):
        uid = uuid4()
        schema = ProjectResponse(
            id=uid,
            title="My project",
            deadline=project_deadline,
            completed=False,
            created_at=now,
            updated_at=now,
        )
        assert schema.id == uid
        assert schema.title == "My project"
        assert schema.completed is False

    def test_creates_from_domain_entity(self, make_project, now):
        project = make_project(title="My project")
        schema = ProjectResponse.model_validate(project)
        assert schema.id == project.id
        assert schema.title == project.title
        assert schema.deadline == project.deadline
        assert schema.completed == project.completed
        assert schema.created_at == project.created_at
        assert schema.updated_at == project.updated_at

    def test_completed_true_serialised_correctly(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        schema = ProjectResponse.model_validate(project)
        assert schema.completed is True

    def test_id_is_uuid(self, make_project):
        schema = ProjectResponse.model_validate(make_project())
        assert isinstance(schema.id, UUID)

    def test_serialises_to_dict(self, make_project):
        schema = ProjectResponse.model_validate(make_project())
        data = schema.model_dump()
        assert "id" in data
        assert "title" in data
        assert "deadline" in data
        assert "completed" in data
        assert "created_at" in data
        assert "updated_at" in data
