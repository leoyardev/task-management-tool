"""
Integration tests for TaskDBModel.

Verifies columns, constraints, defaults, indexes,
relationships, and CRUD behaviour against a real in-memory SQLite DB.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect

from src.adapters.persistence.models.task import TaskDBModel


class TestTaskDBModelSchema:
    def test_table_name_is_tasks(self):
        assert TaskDBModel.__tablename__ == "tasks"

    def test_tasks_table_exists(self, engine):
        assert "tasks" in inspect(engine).get_table_names()

    def test_expected_columns_exist(self, engine):
        columns = {c["name"] for c in inspect(engine).get_columns("tasks")}
        assert columns == {
            "id",
            "title",
            "description",
            "deadline",
            "completed",
            "project_id",
            "created_at",
            "updated_at",
        }

    def test_id_is_primary_key(self, engine):
        pk = inspect(engine).get_pk_constraint("tasks")
        assert "id" in pk["constrained_columns"]

    def test_fk_to_projects_exists(self, engine):
        fks = inspect(engine).get_foreign_keys("tasks")
        assert any(
            fk["referred_table"] == "projects" and fk["name"] == "fk_tasks_project_id"
            for fk in fks
        )


class TestTaskDBModelIndexes:
    def test_idx_tasks_project_id_exists(self, engine):
        index_names = {i["name"] for i in inspect(engine).get_indexes("tasks")}
        assert "idx_tasks_project_id" in index_names

    def test_idx_tasks_completed_exists(self, engine):
        index_names = {i["name"] for i in inspect(engine).get_indexes("tasks")}
        assert "idx_tasks_completed" in index_names

    def test_idx_tasks_deadline_exists(self, engine):
        index_names = {i["name"] for i in inspect(engine).get_indexes("tasks")}
        assert "idx_tasks_deadline" in index_names

    def test_idx_tasks_project_id_covers_correct_column(self, engine):
        indexes = {i["name"]: i for i in inspect(engine).get_indexes("tasks")}
        assert "project_id" in indexes["idx_tasks_project_id"]["column_names"]

    def test_idx_tasks_completed_covers_correct_column(self, engine):
        indexes = {i["name"]: i for i in inspect(engine).get_indexes("tasks")}
        assert "completed" in indexes["idx_tasks_completed"]["column_names"]

    def test_idx_tasks_deadline_covers_correct_column(self, engine):
        indexes = {i["name"]: i for i in inspect(engine).get_indexes("tasks")}
        assert "deadline" in indexes["idx_tasks_deadline"]["column_names"]


class TestTaskDBModelCRUD:
    def test_insert_and_retrieve(self, session, make_task_row):
        session.add(make_task_row(title="My task"))
        session.flush()

        assert session.get(TaskDBModel, "task-1").title == "My task"

    def test_completed_defaults_to_false(self, session, make_task_row):
        session.add(make_task_row())
        session.flush()

        assert session.get(TaskDBModel, "task-1").completed is False

    def test_description_defaults_to_none(self, session, make_task_row):
        session.add(make_task_row())
        session.flush()

        assert session.get(TaskDBModel, "task-1").description is None

    def test_project_id_defaults_to_none(self, session, make_task_row):
        session.add(make_task_row())
        session.flush()

        assert session.get(TaskDBModel, "task-1").project_id is None

    def test_update_title(self, session, make_task_row):
        task = make_task_row()
        session.add(task)
        session.flush()

        task.title = "Updated"
        session.flush()

        assert session.get(TaskDBModel, "task-1").title == "Updated"

    def test_update_completed(self, session, make_task_row):
        task = make_task_row()
        session.add(task)
        session.flush()

        task.completed = True
        session.flush()

        assert session.get(TaskDBModel, "task-1").completed is True

    def test_update_description(self, session, make_task_row):
        task = make_task_row()
        session.add(task)
        session.flush()

        task.description = "Some details"
        session.flush()

        assert session.get(TaskDBModel, "task-1").description == "Some details"

    def test_delete_task(self, session, make_task_row):
        task = make_task_row()
        session.add(task)
        session.flush()

        session.delete(task)
        session.flush()

        assert session.get(TaskDBModel, "task-1") is None

    def test_query_all_tasks(self, session, make_task_row):
        session.add(make_task_row(id="t1", title="Task 1"))
        session.add(make_task_row(id="t2", title="Task 2"))
        session.flush()

        assert len(session.query(TaskDBModel).all()) == 2


class TestTaskDBModelDefaults:
    def test_created_at_is_set_automatically(self, session, make_task_row):
        session.add(make_task_row())
        session.flush()

        assert session.get(TaskDBModel, "task-1").created_at is not None

    def test_updated_at_is_set_automatically(self, session, make_task_row):
        session.add(make_task_row())
        session.flush()

        assert session.get(TaskDBModel, "task-1").updated_at is not None


class TestTaskDBModelConstraints:
    def test_title_cannot_be_null(self, session):
        with pytest.raises(Exception):
            session.add(
                TaskDBModel(
                    id="bad",
                    title=None,
                    deadline=datetime.now(UTC) + timedelta(days=7),
                )
            )
            session.flush()

    def test_deadline_cannot_be_null(self, session):
        with pytest.raises(Exception):
            session.add(
                TaskDBModel(
                    id="bad",
                    title="No deadline",
                    deadline=None,
                )
            )
            session.flush()

    def test_duplicate_id_raises(self, session, make_task_row):
        session.add(make_task_row(id="dup"))
        session.flush()

        with pytest.raises(Exception):
            session.add(make_task_row(id="dup", title="Duplicate"))
            session.flush()

    def test_fk_violation_raises(self, session, make_task_row):
        with pytest.raises(Exception):
            session.add(make_task_row(project_id="nonexistent"))
            session.flush()

    def test_nullable_project_id_allowed(self, session, make_task_row):
        session.add(make_task_row(project_id=None))
        session.flush()

        assert session.get(TaskDBModel, "task-1").project_id is None


class TestTaskDBModelRelationship:
    def test_task_project_is_none_when_unlinked(self, session, make_task_row):
        session.add(make_task_row())
        session.flush()

        assert session.get(TaskDBModel, "task-1").project is None

    def test_task_project_returns_linked_project(
        self, session, make_project_row, make_task_row
    ):
        session.add(make_project_row())
        session.add(make_task_row(project_id="proj-1"))
        session.flush()

        result = session.get(TaskDBModel, "task-1")
        assert result.project is not None
        assert result.project.id == "proj-1"
        assert result.project.title == "Test project"

    def test_unlink_task_from_project(self, session, make_project_row, make_task_row):
        session.add(make_project_row())
        task = make_task_row(project_id="proj-1")
        session.add(task)
        session.flush()

        task.project_id = None
        session.flush()

        assert session.get(TaskDBModel, "task-1").project_id is None

    def test_multiple_tasks_linked_to_same_project(
        self, session, make_project_row, make_task_row
    ):
        session.add(make_project_row())
        session.add(make_task_row(id="t1", project_id="proj-1"))
        session.add(make_task_row(id="t2", project_id="proj-1"))
        session.flush()

        results = session.query(TaskDBModel).filter_by(project_id="proj-1").all()
        assert len(results) == 2

    def test_repr(self, make_task_row):
        task = make_task_row(id="abc", title="My task")
        assert "abc" in repr(task)
        assert "My task" in repr(task)
