"""
Integration tests for SqlTaskRepository.

Tests run against a real in-memory SQLite DB using the
session fixture from conftest — no mocks for persistence.
"""

from datetime import timedelta
from uuid import uuid4

import pytest

from src.adapters.persistence.models.task import TaskDBModel
from src.adapters.persistence.repositories.project import SqlProjectRepository
from src.adapters.persistence.repositories.task import SqlTaskRepository
from src.domain.entities.task import Task
from src.domain.ports.task import (
    BelongsToProjectSpec,
    CompletedTaskSpec,
    OpenTaskSpec,
    OverdueTaskSpec,
)


@pytest.fixture
def repo(session):
    return SqlTaskRepository(session)


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def saved_project(project_repo, make_project):
    project = make_project()
    project_repo.save(project)
    return project


class TestSave:
    def test_inserts_new_task(self, repo, session, make_task):
        task = make_task()
        repo.save(task)
        assert session.get(TaskDBModel, str(task.id)) is not None

    def test_returns_saved_task(self, repo, make_task):
        task = make_task()
        assert repo.save(task) is task

    def test_updates_existing_task(self, repo, make_task):
        task = make_task(title="Old")
        repo.save(task)

        task.update(title="New")
        repo.save(task)

        assert repo.find_by_id(task.id).title == "New"

    def test_save_completed_task(self, repo, make_task):
        task = make_task()
        task.mark_complete()
        task.pull_events()
        repo.save(task)

        assert repo.find_by_id(task.id).completed is True

    def test_save_linked_task(self, repo, make_task, saved_project):
        task = make_task()
        task.link_to_project(saved_project.id, saved_project.deadline)
        repo.save(task)

        assert repo.find_by_id(task.id).project_id == saved_project.id


class TestFindById:
    def test_returns_task_when_found(self, repo, make_task):
        task = make_task()
        repo.save(task)

        result = repo.find_by_id(task.id)
        assert result is not None
        assert result.id == task.id

    def test_returns_none_when_not_found(self, repo):
        assert repo.find_by_id(uuid4()) is None

    def test_returns_domain_entity_not_orm_model(self, repo, make_task):
        task = make_task()
        repo.save(task)

        assert isinstance(repo.find_by_id(task.id), Task)

    def test_maps_all_fields_correctly(self, repo, make_task, now):
        deadline = now + timedelta(days=5)
        task = make_task(title="My task", deadline=deadline, description="Details")
        repo.save(task)

        result = repo.find_by_id(task.id)
        assert result.title == "My task"
        assert result.deadline == deadline
        assert result.description == "Details"
        assert result.completed is False


class TestFindAll:
    def test_returns_empty_list_when_no_tasks(self, repo):
        assert repo.find_all() == []

    def test_returns_all_tasks(self, repo, make_task):
        repo.save(make_task())
        repo.save(make_task())
        repo.save(make_task())

        assert len(repo.find_all()) == 3

    def test_returns_list_of_domain_entities(self, repo, make_task):
        repo.save(make_task())

        assert all(isinstance(t, Task) for t in repo.find_all())

    def test_filter_by_completed_spec(self, repo, make_task, make_completed_task):
        repo.save(make_task())
        repo.save(make_completed_task())

        results = repo.find_all(CompletedTaskSpec())
        assert len(results) == 1
        assert all(t.completed for t in results)

    def test_filter_by_open_spec(self, repo, make_task, make_completed_task):
        repo.save(make_task())
        repo.save(make_completed_task())

        results = repo.find_all(OpenTaskSpec())
        assert len(results) == 1
        assert all(not t.completed for t in results)

    def test_filter_by_overdue_spec(self, repo, make_task, make_overdue_task):
        repo.save(make_task())
        repo.save(make_overdue_task())

        results = repo.find_all(OverdueTaskSpec())
        assert len(results) == 1

    def test_filter_by_belongs_to_project_spec(self, repo, make_task, saved_project):
        linked = make_task()
        linked.link_to_project(saved_project.id, saved_project.deadline)
        repo.save(linked)
        repo.save(make_task())

        results = repo.find_all(BelongsToProjectSpec(saved_project.id))
        assert len(results) == 1
        assert results[0].project_id == saved_project.id

    def test_composed_spec(self, repo, make_task, make_completed_task, saved_project):
        linked_open = make_task()
        linked_open.link_to_project(saved_project.id, saved_project.deadline)
        repo.save(linked_open)

        linked_completed = make_completed_task()
        linked_completed.link_to_project(saved_project.id, saved_project.deadline)
        repo.save(linked_completed)

        repo.save(make_task())

        results = repo.find_all(OpenTaskSpec() & BelongsToProjectSpec(saved_project.id))
        assert len(results) == 1
        assert results[0].project_id == saved_project.id
        assert not results[0].completed


class TestCountOpenByProject:
    def test_returns_zero_when_no_tasks(self, repo, saved_project):
        assert repo.count_open_by_project(saved_project.id) == 0

    def test_counts_only_open_tasks(
        self, repo, make_task, make_completed_task, saved_project
    ):
        open1 = make_task()
        open1.link_to_project(saved_project.id, saved_project.deadline)
        open2 = make_task()
        open2.link_to_project(saved_project.id, saved_project.deadline)
        completed = make_completed_task()
        completed.link_to_project(saved_project.id, saved_project.deadline)

        repo.save(open1)
        repo.save(open2)
        repo.save(completed)

        assert repo.count_open_by_project(saved_project.id) == 2

    def test_does_not_count_tasks_from_other_projects(
        self, repo, make_task, make_project, project_repo, saved_project
    ):
        other_project = make_project()
        project_repo.save(other_project)

        task = make_task()
        task.link_to_project(other_project.id, other_project.deadline)
        repo.save(task)

        assert repo.count_open_by_project(saved_project.id) == 0


class TestFindExceedingDeadline:
    def test_returns_tasks_exceeding_deadline(
        self, repo, make_task, saved_project, now
    ):
        early = make_task(deadline=now + timedelta(days=5))
        early.link_to_project(saved_project.id, saved_project.deadline)
        late = make_task(deadline=now + timedelta(days=25))
        late.link_to_project(saved_project.id, saved_project.deadline)
        repo.save(early)
        repo.save(late)

        cutoff = now + timedelta(days=10)
        results = repo.find_exceeding_deadline(saved_project.id, cutoff)
        assert len(results) == 1
        assert results[0].id == late.id

    def test_returns_empty_when_none_exceed(self, repo, make_task, saved_project, now):
        task = make_task(deadline=now + timedelta(days=5))
        task.link_to_project(saved_project.id, saved_project.deadline)
        repo.save(task)

        cutoff = now + timedelta(days=10)
        assert repo.find_exceeding_deadline(saved_project.id, cutoff) == []

    def test_does_not_include_tasks_from_other_projects(
        self, repo, make_task, make_project, project_repo, saved_project, now
    ):
        other = make_project()
        project_repo.save(other)

        task = make_task(deadline=now + timedelta(days=25))
        task.link_to_project(other.id, other.deadline)
        repo.save(task)

        cutoff = now + timedelta(days=10)
        assert repo.find_exceeding_deadline(saved_project.id, cutoff) == []


class TestDelete:
    def test_deletes_existing_task(self, repo, make_task):
        task = make_task()
        repo.save(task)

        repo.delete(task.id)

        assert repo.find_by_id(task.id) is None

    def test_delete_nonexistent_task_does_not_raise(self, repo):
        repo.delete(uuid4())

    def test_does_not_delete_other_tasks(self, repo, make_task):
        keep = make_task()
        remove = make_task()
        repo.save(keep)
        repo.save(remove)

        repo.delete(remove.id)

        assert repo.find_by_id(keep.id) is not None
