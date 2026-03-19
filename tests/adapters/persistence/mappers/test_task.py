"""
Unit tests for TaskMapper.

Verifies correct conversion between TaskDBModel and Task
in both directions, and that update_db_model mutates correctly.
"""

from datetime import timedelta
from uuid import UUID, uuid4

from src.adapters.persistence.mappers.task import TaskMapper
from src.adapters.persistence.models.task import TaskDBModel
from src.domain.entities.task import Task


class TestToDomain:
    def test_returns_task_instance(self, make_task_row):
        assert isinstance(TaskMapper.to_domain(make_task_row()), Task)

    def test_id_converted_to_uuid(self, make_task_row):
        db_model = make_task_row()
        result = TaskMapper.to_domain(db_model)
        assert isinstance(result.id, UUID)
        assert str(result.id) == db_model.id

    def test_title_mapped_correctly(self, make_task_row):
        assert TaskMapper.to_domain(make_task_row(title="My task")).title == "My task"

    def test_description_mapped_correctly(self, make_task_row):
        assert (
            TaskMapper.to_domain(make_task_row(description="Details")).description
            == "Details"
        )

    def test_description_none_when_not_set(self, make_task_row):
        assert TaskMapper.to_domain(make_task_row()).description is None

    def test_deadline_mapped_correctly(self, make_task_row, now):
        deadline = now + timedelta(days=5)
        assert (
            TaskMapper.to_domain(make_task_row(deadline=deadline)).deadline == deadline
        )

    def test_completed_mapped_correctly(self, make_task_row):
        assert TaskMapper.to_domain(make_task_row(completed=True)).completed is True

    def test_project_id_converted_to_uuid(self, make_task_row, project_id):
        db_model = make_task_row(project_id=str(project_id))
        result = TaskMapper.to_domain(db_model)
        assert isinstance(result.project_id, UUID)
        assert result.project_id == project_id

    def test_project_id_none_when_not_set(self, make_task_row):
        assert TaskMapper.to_domain(make_task_row()).project_id is None

    def test_created_at_mapped_correctly(self, make_task_row, now):
        assert TaskMapper.to_domain(make_task_row(created_at=now)).created_at == now

    def test_updated_at_mapped_correctly(self, make_task_row, now):
        assert TaskMapper.to_domain(make_task_row(updated_at=now)).updated_at == now

    def test_round_trip_preserves_all_fields(self, make_task_row, project_id):
        original = make_task_row(project_id=str(project_id))
        restored = TaskMapper.to_db_model(TaskMapper.to_domain(original))
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.description == original.description
        assert restored.deadline == original.deadline
        assert restored.completed == original.completed
        assert restored.project_id == original.project_id
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at


class TestToDbModel:
    def test_returns_task_db_model_instance(self, make_task):
        assert isinstance(TaskMapper.to_db_model(make_task()), TaskDBModel)

    def test_id_converted_to_string(self, make_task):
        task = make_task()
        result = TaskMapper.to_db_model(task)
        assert isinstance(result.id, str)
        assert result.id == str(task.id)

    def test_title_mapped_correctly(self, make_task):
        assert TaskMapper.to_db_model(make_task(title="My task")).title == "My task"

    def test_description_mapped_correctly(self, make_task):
        assert (
            TaskMapper.to_db_model(make_task(description="Details")).description
            == "Details"
        )

    def test_description_none_when_not_set(self, make_task):
        assert TaskMapper.to_db_model(make_task()).description is None

    def test_deadline_mapped_correctly(self, make_task, now):
        deadline = now + timedelta(days=5)
        assert TaskMapper.to_db_model(make_task(deadline=deadline)).deadline == deadline

    def test_completed_mapped_correctly(self, make_completed_task):
        assert TaskMapper.to_db_model(make_completed_task()).completed is True

    def test_project_id_converted_to_string(self, make_linked_task, project_id):
        result = TaskMapper.to_db_model(make_linked_task(project_id=project_id))
        assert isinstance(result.project_id, str)
        assert result.project_id == str(project_id)

    def test_project_id_none_when_not_linked(self, make_task):
        assert TaskMapper.to_db_model(make_task()).project_id is None

    def test_created_at_mapped_correctly(self, make_task):
        task = make_task()
        assert TaskMapper.to_db_model(task).created_at == task.created_at

    def test_updated_at_mapped_correctly(self, make_task):
        task = make_task()
        assert TaskMapper.to_db_model(task).updated_at == task.updated_at


class TestUpdateDbModel:
    def test_returns_same_instance(self, make_task_row, make_task):
        db_model = make_task_row()
        assert TaskMapper.update_db_model(db_model, make_task()) is db_model

    def test_updates_title(self, make_task_row, make_task):
        db_model = make_task_row(title="Old")
        TaskMapper.update_db_model(db_model, make_task(title="New"))
        assert db_model.title == "New"

    def test_updates_description(self, make_task_row, make_task):
        db_model = make_task_row()
        TaskMapper.update_db_model(db_model, make_task(description="Updated"))
        assert db_model.description == "Updated"

    def test_clears_description_when_none(self, make_task_row, make_task):
        db_model = make_task_row(description="Old")
        TaskMapper.update_db_model(db_model, make_task())
        assert db_model.description is None

    def test_updates_deadline(self, make_task_row, make_task, now):
        new_deadline = now + timedelta(days=3)
        db_model = make_task_row()
        TaskMapper.update_db_model(db_model, make_task(deadline=new_deadline))
        assert db_model.deadline == new_deadline

    def test_updates_completed(self, make_task_row, make_completed_task):
        db_model = make_task_row(completed=False)
        TaskMapper.update_db_model(db_model, make_completed_task())
        assert db_model.completed is True

    def test_updates_project_id(self, make_task_row, make_linked_task, project_id):
        db_model = make_task_row()
        TaskMapper.update_db_model(db_model, make_linked_task(project_id=project_id))
        assert db_model.project_id == str(project_id)

    def test_clears_project_id_when_unlinked(self, make_task_row, make_task):
        db_model = make_task_row()
        TaskMapper.update_db_model(db_model, make_task())
        assert db_model.project_id is None

    def test_updates_updated_at(self, make_task_row, make_task, now):
        db_model = make_task_row(updated_at=now - timedelta(hours=1))
        task = make_task()
        task.update(title="New")
        TaskMapper.update_db_model(db_model, task)
        assert db_model.updated_at > now - timedelta(hours=1)

    def test_does_not_change_id(self, make_task_row, make_task):
        original_id = str(uuid4())
        db_model = make_task_row(id=original_id)
        TaskMapper.update_db_model(db_model, make_task())
        assert db_model.id == original_id

    def test_does_not_change_created_at(self, make_task_row, make_task, now):
        original_created_at = now - timedelta(days=5)
        db_model = make_task_row(created_at=original_created_at)
        TaskMapper.update_db_model(db_model, make_task())
        assert db_model.created_at == original_created_at
