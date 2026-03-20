"""
Unit tests for v1 task schemas.

Verifies validation rules on TaskCreate, TaskUpdate,
TaskResponse and TaskFiltersQuery.
"""

from uuid import UUID

import pytest

from src.adapters.api.v1.schemas.task import (
    TaskCreate,
    TaskFiltersQuery,
    TaskResponse,
    TaskUpdate,
)


class TestTaskCreate:
    def test_valid_with_required_fields(self, now, project_deadline):
        schema = TaskCreate(title="My task", deadline=project_deadline)
        assert schema.title == "My task"
        assert schema.deadline == project_deadline

    def test_description_defaults_to_none(self, project_deadline):
        schema = TaskCreate(title="My task", deadline=project_deadline)
        assert schema.description is None

    def test_project_id_defaults_to_none(self, project_deadline):
        schema = TaskCreate(title="My task", deadline=project_deadline)
        assert schema.project_id is None

    def test_valid_with_all_fields(self, project_deadline, project_id):
        schema = TaskCreate(
            title="My task",
            deadline=project_deadline,
            description="Some details",
            project_id=project_id,
        )
        assert schema.description == "Some details"
        assert schema.project_id == project_id

    def test_missing_title_raises(self, project_deadline):
        with pytest.raises(Exception):
            TaskCreate(deadline=project_deadline)

    def test_missing_deadline_raises(self):
        with pytest.raises(Exception):
            TaskCreate(title="My task")

    def test_empty_title_raises(self, project_deadline):
        with pytest.raises(Exception):
            TaskCreate(title="", deadline=project_deadline)

    def test_title_exceeding_max_length_raises(self, project_deadline):
        with pytest.raises(Exception):
            TaskCreate(title="x" * 256, deadline=project_deadline)

    def test_title_at_max_length_is_valid(self, project_deadline):
        schema = TaskCreate(title="x" * 255, deadline=project_deadline)
        assert len(schema.title) == 255


class TestTaskUpdate:
    def test_valid_with_title_only(self):
        schema = TaskUpdate(title="New title")
        assert schema.title == "New title"
        assert schema.description is None
        assert schema.deadline is None

    def test_valid_with_description_only(self):
        schema = TaskUpdate(description="New description")
        assert schema.description == "New description"

    def test_valid_with_deadline_only(self, project_deadline):
        schema = TaskUpdate(deadline=project_deadline)
        assert schema.deadline == project_deadline

    def test_valid_with_all_fields(self, project_deadline):
        schema = TaskUpdate(
            title="New title",
            description="New description",
            deadline=project_deadline,
        )
        assert schema.title == "New title"
        assert schema.description == "New description"
        assert schema.deadline == project_deadline

    def test_raises_when_no_fields_provided(self):
        with pytest.raises(Exception, match="At least one field"):
            TaskUpdate()

    def test_empty_title_raises(self):
        with pytest.raises(Exception):
            TaskUpdate(title="")

    def test_title_exceeding_max_length_raises(self):
        with pytest.raises(Exception):
            TaskUpdate(title="x" * 256)

    def test_title_at_max_length_is_valid(self):
        schema = TaskUpdate(title="x" * 255)
        assert len(schema.title) == 255


class TestTaskResponse:
    def test_creates_from_domain_entity(self, make_task):
        task = make_task(title="My task")
        schema = TaskResponse.model_validate(task)
        assert schema.id == task.id
        assert schema.title == task.title
        assert schema.deadline == task.deadline
        assert schema.completed == task.completed
        assert schema.description == task.description
        assert schema.project_id == task.project_id
        assert schema.created_at == task.created_at
        assert schema.updated_at == task.updated_at

    def test_description_none_when_not_set(self, make_task):
        schema = TaskResponse.model_validate(make_task())
        assert schema.description is None

    def test_project_id_none_when_not_linked(self, make_task):
        schema = TaskResponse.model_validate(make_task())
        assert schema.project_id is None

    def test_project_id_set_when_linked(
        self, make_linked_task, project_id, project_deadline
    ):
        task = make_linked_task(
            project_id=project_id, project_deadline=project_deadline
        )
        schema = TaskResponse.model_validate(task)
        assert schema.project_id == project_id

    def test_completed_true_when_task_completed(self, make_completed_task):
        schema = TaskResponse.model_validate(make_completed_task())
        assert schema.completed is True

    def test_id_is_uuid(self, make_task):
        schema = TaskResponse.model_validate(make_task())
        assert isinstance(schema.id, UUID)

    def test_serialises_to_dict(self, make_task):
        data = TaskResponse.model_validate(make_task()).model_dump()
        assert all(
            k in data
            for k in [
                "id",
                "title",
                "description",
                "deadline",
                "completed",
                "project_id",
                "created_at",
                "updated_at",
            ]
        )


class TestTaskFiltersQuery:
    def test_all_fields_default_to_none(self):
        filters = TaskFiltersQuery()
        assert filters.completed is None
        assert filters.overdue is None
        assert filters.project_id is None

    def test_completed_filter(self):
        assert TaskFiltersQuery(completed=True).completed is True
        assert TaskFiltersQuery(completed=False).completed is False

    def test_overdue_filter(self):
        assert TaskFiltersQuery(overdue=True).overdue is True

    def test_project_id_filter(self, project_id):
        filters = TaskFiltersQuery(project_id=project_id)
        assert filters.project_id == project_id

    def test_all_filters_set_together(self, project_id):
        filters = TaskFiltersQuery(
            completed=False,
            overdue=True,
            project_id=project_id,
        )
        assert filters.completed is False
        assert filters.overdue is True
        assert filters.project_id == project_id
