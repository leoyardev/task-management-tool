"""
Integration tests for SqlProjectRepository.
Tests run against a real in-memory SQLite DB using the
session fixture from conftest — no mocks for persistence.
"""

from uuid import uuid4

import pytest

from src.adapters.persistence.models.project import ProjectDBModel
from src.adapters.persistence.repositories.project import SqlProjectRepository
from src.domain.entities.project import Project


@pytest.fixture
def repo(session):
    return SqlProjectRepository(session)


class TestSave:
    def test_inserts_new_project(self, repo, session, make_project):
        project = make_project()
        repo.save(project)

        assert session.get(ProjectDBModel, str(project.id)) is not None

    def test_returns_saved_project(self, repo, make_project):
        project = make_project()
        result = repo.save(project)
        assert result is project

    def test_updates_existing_project(self, repo, make_project):
        project = make_project(title="Old")
        repo.save(project)

        project.update(title="New")
        repo.save(project)

        found = repo.find_by_id(project.id)
        assert found.title == "New"

    def test_save_completed_project(self, repo, make_project):
        project = make_project()
        project.mark_complete(open_task_count=0)
        project.pull_events()
        repo.save(project)

        found = repo.find_by_id(project.id)
        assert found.completed is True


class TestFindById:
    def test_returns_project_when_found(self, repo, make_project):
        project = make_project()
        repo.save(project)

        result = repo.find_by_id(project.id)
        assert result is not None
        assert result.id == project.id

    def test_returns_none_when_not_found(self, repo):
        assert repo.find_by_id(uuid4()) is None

    def test_returns_domain_entity_not_orm_model(self, repo, make_project):
        project = make_project()
        repo.save(project)

        result = repo.find_by_id(project.id)
        assert isinstance(result, Project)

    def test_maps_all_fields_correctly(self, repo, make_project, project_deadline):
        project = make_project(title="My project", deadline=project_deadline)
        repo.save(project)

        result = repo.find_by_id(project.id)
        assert result.title == "My project"
        assert result.deadline == project_deadline
        assert result.completed is False


class TestFindAll:
    def test_returns_empty_list_when_no_projects(self, repo):
        assert repo.find_all() == []

    def test_returns_all_projects(self, repo, make_project):
        repo.save(make_project(title="Project 1"))
        repo.save(make_project(title="Project 2"))
        repo.save(make_project(title="Project 3"))

        results = repo.find_all()
        assert len(results) == 3

    def test_returns_list_of_domain_entities(self, repo, make_project):
        repo.save(make_project())

        results = repo.find_all()
        assert all(isinstance(p, Project) for p in results)

    def test_returns_correct_titles(self, repo, make_project):
        repo.save(make_project(title="Alpha"))
        repo.save(make_project(title="Beta"))

        titles = {p.title for p in repo.find_all()}
        assert titles == {"Alpha", "Beta"}


class TestDelete:
    def test_deletes_existing_project(self, repo, make_project):
        project = make_project()
        repo.save(project)

        repo.delete(project.id)

        assert repo.find_by_id(project.id) is None

    def test_delete_nonexistent_project_does_not_raise(self, repo):
        repo.delete(uuid4())

    def test_does_not_delete_other_projects(self, repo, make_project):
        project1 = make_project(title="Keep")
        project2 = make_project(title="Delete")
        repo.save(project1)
        repo.save(project2)

        repo.delete(project2.id)

        assert repo.find_by_id(project1.id) is not None
