from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.domain.entities.project import Project


class ProjectRepository(ABC):
    """
    Port — defines what any project persistence implementation must provide.

    The domain and application layers depend only on this interface.
    The actual implementation lives in adapters/persistence/ and is
    injected at startup via dependency injection.
    """

    @abstractmethod
    def save(self, project: Project) -> Project:
        """Insert or update a project. Returns the saved project."""
        pass

    @abstractmethod
    def find_by_id(self, project_id: UUID) -> Optional[Project]:
        """Return a project by id, or None if not found."""
        pass

    @abstractmethod
    def find_all(self) -> list[Project]:
        """Return all projects."""
        pass

    @abstractmethod
    def delete(self, project_id: UUID) -> None:
        """Delete a project by id."""
        pass