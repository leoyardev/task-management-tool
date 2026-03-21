"""
Unit tests for TaskRepository specifications and port contract.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.domain.entities.task import Task
from src.domain.ports.task import (
    BelongsToProjectSpec,
    CompletedTaskSpec,
    OpenTaskSpec,
    OverdueTaskSpec,
    TaskRepository,
    UnlinkedTaskSpec,
)

PROJECT_ID = uuid4()
NOW = datetime.now(UTC)


def make_task(**kwargs) -> Task:
    return Task.create(
        title=kwargs.pop("title", "Test task"),
        deadline=kwargs.pop("deadline", NOW + timedelta(days=7)),
        **kwargs,
    )


def make_completed_task(**kwargs) -> Task:
    task = make_task(**kwargs)
    task.mark_complete()
    task.pull_events()
    return task


def make_overdue_task(**kwargs) -> Task:
    return make_task(deadline=NOW - timedelta(days=1), **kwargs)


def make_linked_task(**kwargs) -> Task:
    return make_task(
        project_id=PROJECT_ID,
        project_deadline=NOW + timedelta(days=30),
        **kwargs,
    )


class TestTaskRepositoryPort:
    def test_cannot_instantiate_without_implementation(self):
        with pytest.raises(TypeError):
            TaskRepository()

    def test_concrete_class_missing_method_raises(self):
        class IncompleteRepo(TaskRepository):
            def save(self, task):
                pass

            def find_by_id(self, task_id):
                pass

            def find_all(self, spec=None):
                pass

            def count_open_by_project(self, project_id):
                pass

            def find_exceeding_deadline(self, project_id, deadline):
                pass

        with pytest.raises(TypeError):
            IncompleteRepo()


class TestSpecifications:
    def test_completed_spec_matches_completed_task(self):
        assert CompletedTaskSpec().is_satisfied_by(make_completed_task()) is True

    def test_completed_spec_does_not_match_open_task(self):
        assert CompletedTaskSpec().is_satisfied_by(make_task()) is False

    def test_open_spec_matches_open_task(self):
        assert OpenTaskSpec().is_satisfied_by(make_task()) is True

    def test_open_spec_does_not_match_completed_task(self):
        assert OpenTaskSpec().is_satisfied_by(make_completed_task()) is False

    def test_overdue_spec_matches_past_deadline_open_task(self):
        assert OverdueTaskSpec().is_satisfied_by(make_overdue_task()) is True

    def test_overdue_spec_does_not_match_completed_overdue_task(self):
        task = make_overdue_task()
        task.mark_complete()
        task.pull_events()
        assert OverdueTaskSpec().is_satisfied_by(task) is False

    def test_belongs_to_project_spec_matches_correct_project(self):
        assert (
            BelongsToProjectSpec(PROJECT_ID).is_satisfied_by(make_linked_task()) is True
        )

    def test_belongs_to_project_spec_does_not_match_unlinked(self):
        assert BelongsToProjectSpec(PROJECT_ID).is_satisfied_by(make_task()) is False

    def test_unlinked_spec_matches_task_with_no_project(self):
        assert UnlinkedTaskSpec().is_satisfied_by(make_task()) is True

    def test_unlinked_spec_does_not_match_linked_task(self):
        assert UnlinkedTaskSpec().is_satisfied_by(make_linked_task()) is False


class TestComposition:
    def test_and_both_satisfied(self):
        task = make_overdue_task(
            project_id=PROJECT_ID,
            project_deadline=NOW + timedelta(days=30),
        )
        spec = OverdueTaskSpec() & BelongsToProjectSpec(PROJECT_ID)
        assert spec.is_satisfied_by(task) is True

    def test_and_one_fails(self):
        task = make_task()  # not overdue
        spec = OverdueTaskSpec() & BelongsToProjectSpec(PROJECT_ID)
        assert spec.is_satisfied_by(task) is False

    def test_or_one_satisfied(self):
        task = make_completed_task()  # completed but not linked
        spec = CompletedTaskSpec() | BelongsToProjectSpec(PROJECT_ID)
        assert spec.is_satisfied_by(task) is True

    def test_or_both_fail(self):
        task = make_task()  # open and unlinked
        spec = CompletedTaskSpec() | BelongsToProjectSpec(PROJECT_ID)
        assert spec.is_satisfied_by(task) is False

    def test_not_inverts_result(self):
        task = make_task()  # open
        assert (~CompletedTaskSpec()).is_satisfied_by(task) is True

    def test_complex_composition(self):
        """Open, overdue, belonging to project — real world use case."""
        task = make_overdue_task(
            project_id=PROJECT_ID,
            project_deadline=NOW + timedelta(days=30),
        )
        spec = OpenTaskSpec() & OverdueTaskSpec() & BelongsToProjectSpec(PROJECT_ID)
        assert spec.is_satisfied_by(task) is True
