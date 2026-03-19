"""
Unit tests for ProjectMapper.

Verifies correct conversion between ProjectDBModel and Project
in both directions, and that update_db_model mutates correctly.
"""

from datetime import timedelta
from uuid import UUID, uuid4

from src.adapters.persistence.mappers.project import ProjectMapper
from src.adapters.persistence.models.project import ProjectDBModel
from src.domain.entities.project import Project


class TestToDomain:
    def test_returns_project_instance(self, make_project_row):
        assert isinstance(ProjectMapper.to_domain(make_project_row()), Project)

    def test_id_converted_to_uuid(self, make_project_row):
        db_model = make_project_row()
        result = ProjectMapper.to_domain(db_model)
        assert isinstance(result.id, UUID)
        assert str(result.id) == db_model.id

    def test_title_mapped_correctly(self, make_project_row):
        result = ProjectMapper.to_domain(make_project_row(title="My project"))
        assert result.title == "My project"

    def test_deadline_mapped_correctly(self, make_project_row, project_deadline):
        result = ProjectMapper.to_domain(make_project_row(deadline=project_deadline))
        assert result.deadline == project_deadline

    def test_completed_mapped_correctly(self, make_project_row):
        result = ProjectMapper.to_domain(make_project_row(completed=True))
        assert result.completed is True

    def test_created_at_mapped_correctly(self, make_project_row, now):
        result = ProjectMapper.to_domain(make_project_row(created_at=now))
        assert result.created_at == now

    def test_updated_at_mapped_correctly(self, make_project_row, now):
        result = ProjectMapper.to_domain(make_project_row(updated_at=now))
        assert result.updated_at == now

    def test_round_trip_preserves_all_fields(self, make_project_row):
        original = make_project_row()
        restored = ProjectMapper.to_db_model(ProjectMapper.to_domain(original))
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.deadline == original.deadline
        assert restored.completed == original.completed
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at


class TestToDbModel:
    def test_returns_project_db_model_instance(self, make_project):
        assert isinstance(ProjectMapper.to_db_model(make_project()), ProjectDBModel)

    def test_id_converted_to_string(self, make_project):
        project = make_project()
        result = ProjectMapper.to_db_model(project)
        assert isinstance(result.id, str)
        assert result.id == str(project.id)

    def test_title_mapped_correctly(self, make_project):
        result = ProjectMapper.to_db_model(make_project(title="My project"))
        assert result.title == "My project"

    def test_deadline_mapped_correctly(self, make_project, project_deadline):
        result = ProjectMapper.to_db_model(make_project(deadline=project_deadline))
        assert result.deadline == project_deadline

    def test_completed_mapped_correctly(self, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        assert ProjectMapper.to_db_model(project).completed is True

    def test_created_at_mapped_correctly(self, make_project):
        project = make_project()
        assert ProjectMapper.to_db_model(project).created_at == project.created_at

    def test_updated_at_mapped_correctly(self, make_project):
        project = make_project()
        assert ProjectMapper.to_db_model(project).updated_at == project.updated_at


class TestUpdateDbModel:
    def test_returns_same_instance(self, make_project_row, make_project):
        db_model = make_project_row()
        result = ProjectMapper.update_db_model(db_model, make_project())
        assert result is db_model

    def test_updates_title(self, make_project_row, make_project):
        db_model = make_project_row(title="Old")
        ProjectMapper.update_db_model(db_model, make_project(title="New"))
        assert db_model.title == "New"

    def test_updates_deadline(
        self, make_project_row, make_project, project_deadline, now
    ):
        db_model = make_project_row(deadline=project_deadline)
        new_deadline = project_deadline - timedelta(days=5)
        ProjectMapper.update_db_model(db_model, make_project(deadline=new_deadline))
        assert db_model.deadline == new_deadline

    def test_updates_completed(self, make_project_row, make_project):
        db_model = make_project_row(completed=False)
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        ProjectMapper.update_db_model(db_model, project)
        assert db_model.completed is True

    def test_updates_updated_at(self, make_project_row, make_project, now):
        db_model = make_project_row(updated_at=now - timedelta(hours=1))
        project = make_project()
        project.update(title="New")
        ProjectMapper.update_db_model(db_model, project)
        assert db_model.updated_at > now - timedelta(hours=1)

    def test_does_not_change_id(self, make_project_row, make_project):
        original_id = str(uuid4())
        db_model = make_project_row(id=original_id)
        ProjectMapper.update_db_model(db_model, make_project())
        assert db_model.id == original_id

    def test_does_not_change_created_at(self, make_project_row, make_project, now):
        original_created_at = now - timedelta(days=5)
        db_model = make_project_row(created_at=original_created_at)
        ProjectMapper.update_db_model(db_model, make_project())
        assert db_model.created_at == original_created_at
