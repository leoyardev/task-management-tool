"""
Integration tests for ProjectDBModel.

Verifies columns, constraints, defaults, relationships,
and CRUD behaviour against a real in-memory SQLite DB.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect

from src.adapters.persistence.models.project import ProjectDBModel
from src.adapters.persistence.models.task import TaskDBModel


class TestProjectDBModelSchema:
    def test_table_name_is_projects(self):
        assert ProjectDBModel.__tablename__ == "projects"

    def test_projects_table_exists(self, engine):
        assert "projects" in inspect(engine).get_table_names()

    def test_expected_columns_exist(self, engine):
        columns = {c["name"] for c in inspect(engine).get_columns("projects")}
        assert columns == {
            "id",
            "title",
            "deadline",
            "completed",
            "created_at",
            "updated_at",
        }

    def test_id_is_primary_key(self, engine):
        pk = inspect(engine).get_pk_constraint("projects")
        assert "id" in pk["constrained_columns"]

    def test_no_foreign_keys_on_projects(self, engine):
        assert inspect(engine).get_foreign_keys("projects") == []


class TestProjectDBModelCRUD:
    def test_insert_and_retrieve(self, session, make_project_row):
        project = make_project_row(title="My project")
        session.add(project)
        session.flush()

        result = session.get(ProjectDBModel, project.id)
        assert result.title == "My project"

    def test_completed_defaults_to_false(self, session, make_project_row):
        project = make_project_row()
        session.add(project)
        session.flush()

        assert session.get(ProjectDBModel, project.id).completed is False

    def test_update_title(self, session, make_project_row):
        project = make_project_row()
        session.add(project)
        session.flush()

        project.title = "Updated"
        session.flush()

        assert session.get(ProjectDBModel, project.id).title == "Updated"

    def test_update_completed(self, session, make_project_row):
        project = make_project_row()
        session.add(project)
        session.flush()

        project.completed = True
        session.flush()

        assert session.get(ProjectDBModel, project.id).completed is True

    def test_delete_project(self, session, make_project_row):
        project = make_project_row()
        session.add(project)
        session.flush()

        session.delete(project)
        session.flush()

        assert session.get(ProjectDBModel, project.id) is None

    def test_query_all_projects(self, session, make_project_row):
        session.add(make_project_row())
        session.add(make_project_row())
        session.flush()

        assert len(session.query(ProjectDBModel).all()) == 2


class TestProjectDBModelDefaults:
    def test_created_at_is_set_automatically(self, session, make_project_row):
        project = make_project_row()
        session.add(project)
        session.flush()

        assert session.get(ProjectDBModel, project.id).created_at is not None

    def test_updated_at_is_set_automatically(self, session, make_project_row):
        project = make_project_row()
        session.add(project)
        session.flush()

        assert session.get(ProjectDBModel, project.id).updated_at is not None

    def test_completed_server_default_is_false(self, session, make_project_row):
        project = make_project_row()
        session.add(project)
        session.flush()

        assert session.get(ProjectDBModel, project.id).completed is False


class TestProjectDBModelConstraints:
    def test_title_cannot_be_null(self, session):
        with pytest.raises(Exception):
            session.add(
                ProjectDBModel(
                    id="proj-bad",
                    title=None,
                    deadline=datetime.now(UTC) + timedelta(days=30),
                )
            )
            session.flush()

    def test_deadline_cannot_be_null(self, session):
        with pytest.raises(Exception):
            session.add(
                ProjectDBModel(
                    id="proj-bad",
                    title="No deadline",
                    deadline=None,
                )
            )
            session.flush()

    def test_duplicate_id_raises(self, session, make_project_row):
        project = make_project_row()
        session.add(project)
        session.flush()
        session.expunge(project)  # remove from identity map

        with pytest.raises(Exception):
            session.add(make_project_row(id=project.id))
            session.flush()


class TestProjectDBModelRelationship:
    def test_project_has_empty_tasks_by_default(self, session, make_project_row):
        project = make_project_row()
        session.add(project)
        session.flush()

        assert session.get(ProjectDBModel, project.id).tasks == []

    def test_project_tasks_returns_linked_tasks(
        self, session, make_project_row, make_task_row
    ):
        project = make_project_row()
        session.add(project)
        session.add(make_task_row(project_id=project.id, title="Task 1"))
        session.add(make_task_row(project_id=project.id, title="Task 2"))
        session.flush()

        result = session.get(ProjectDBModel, project.id)
        assert len(result.tasks) == 2
        assert {t.title for t in result.tasks} == {"Task 1", "Task 2"}

    def test_deleting_project_does_not_cascade_to_tasks(
        self, session, make_project_row, make_task_row
    ):
        project = make_project_row()
        task = make_task_row(project_id=project.id)
        session.add(project)
        session.add(task)
        session.flush()

        task.project_id = None
        session.flush()
        session.delete(project)
        session.flush()

        assert session.get(TaskDBModel, task.id) is not None

    def test_repr(self, make_project_row):
        project = make_project_row(title="My project")
        assert project.id in repr(project)
        assert "My project" in repr(project)
