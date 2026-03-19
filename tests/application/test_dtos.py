"""
Unit tests for application DTOs.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from src.application.dtos import (
    CreateProjectDTO,
    CreateTaskDTO,
    UpdateProjectDTO,
    UpdateTaskDTO,
)


class TestCreateProjectDTO:
    def test_creates_with_required_fields(self):
        dto = CreateProjectDTO(
            title="Launch app",
            deadline=datetime(2025, 12, 1),
        )
        assert dto.title == "Launch app"
        assert dto.deadline == datetime(2025, 12, 1)

    def test_missing_title_raises(self):
        with pytest.raises(TypeError):
            CreateProjectDTO(deadline=datetime(2025, 12, 1))

    def test_missing_deadline_raises(self):
        with pytest.raises(TypeError):
            CreateProjectDTO(title="Launch app")


class TestUpdateProjectDTO:
    def test_all_fields_optional(self):
        dto = UpdateProjectDTO()
        assert dto.title is None
        assert dto.deadline is None

    def test_creates_with_title_only(self):
        dto = UpdateProjectDTO(title="New title")
        assert dto.title == "New title"
        assert dto.deadline is None

    def test_creates_with_deadline_only(self):
        dto = UpdateProjectDTO(deadline=datetime(2025, 12, 1))
        assert dto.title is None
        assert dto.deadline == datetime(2025, 12, 1)

    def test_creates_with_all_fields(self):
        dto = UpdateProjectDTO(
            title="New title",
            deadline=datetime(2025, 12, 1),
        )
        assert dto.title == "New title"
        assert dto.deadline == datetime(2025, 12, 1)


class TestCreateTaskDTO:
    def test_creates_with_required_fields(self):
        dto = CreateTaskDTO(
            title="Write tests",
            deadline=datetime(2025, 11, 1),
        )
        assert dto.title == "Write tests"
        assert dto.deadline == datetime(2025, 11, 1)

    def test_description_defaults_to_none(self):
        dto = CreateTaskDTO(title="Write tests", deadline=datetime(2025, 11, 1))
        assert dto.description is None

    def test_project_id_defaults_to_none(self):
        dto = CreateTaskDTO(title="Write tests", deadline=datetime(2025, 11, 1))
        assert dto.project_id is None

    def test_creates_with_all_fields(self):
        project_id = uuid4()
        dto = CreateTaskDTO(
            title="Write tests",
            deadline=datetime(2025, 11, 1),
            description="Some details",
            project_id=project_id,
        )
        assert dto.description == "Some details"
        assert dto.project_id == project_id

    def test_missing_title_raises(self):
        with pytest.raises(TypeError):
            CreateTaskDTO(deadline=datetime(2025, 11, 1))

    def test_missing_deadline_raises(self):
        with pytest.raises(TypeError):
            CreateTaskDTO(title="Write tests")


class TestUpdateTaskDTO:
    def test_all_fields_optional(self):
        dto = UpdateTaskDTO()
        assert dto.title is None
        assert dto.description is None
        assert dto.deadline is None

    def test_creates_with_title_only(self):
        dto = UpdateTaskDTO(title="New title")
        assert dto.title == "New title"
        assert dto.description is None
        assert dto.deadline is None

    def test_creates_with_all_fields(self):
        dto = UpdateTaskDTO(
            title="New title",
            description="New description",
            deadline=datetime(2025, 11, 1),
        )
        assert dto.title == "New title"
        assert dto.description == "New description"
        assert dto.deadline == datetime(2025, 11, 1)
