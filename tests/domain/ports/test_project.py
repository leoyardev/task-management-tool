"""
Unit tests for ProjectRepository port contract.
"""
import pytest

from src.domain.ports.project import ProjectRepository



class TestProjectRepositoryPort:

    def test_cannot_instantiate_without_implementation(self):
        with pytest.raises(TypeError):
            ProjectRepository()

    def test_concrete_class_missing_method_raises(self):
        class IncompleteRepo(ProjectRepository):
            def save(self, project): ...
            def find_by_id(self, project_id): ...
            def find_all(self): ...
            # delete() missing

        with pytest.raises(TypeError):
            IncompleteRepo()

    def test_concrete_class_with_all_methods_can_instantiate(self):
        class FullRepo(ProjectRepository):
            def save(self, project): ...
            def find_by_id(self, project_id): ...
            def find_all(self): ...
            def delete(self, project_id): ...

        assert FullRepo() is not None