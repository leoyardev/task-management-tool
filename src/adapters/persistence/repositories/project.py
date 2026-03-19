from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.adapters.persistence.mappers.project import ProjectMapper
from src.adapters.persistence.models.project import ProjectDBModel
from src.domain.entities.project import Project
from src.domain.ports.project import ProjectRepository


class SqlProjectRepository(ProjectRepository):
    """
    SQLAlchemy implementation of the ProjectRepository port.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, project: Project) -> Project:
        existing = self._session.get(ProjectDBModel, str(project.id))
        if existing:
            ProjectMapper.update_db_model(existing, project)
        else:
            self._session.add(ProjectMapper.to_db_model(project))
        self._session.flush()
        return project

    def find_by_id(self, project_id: UUID) -> Optional[Project]:
        db_model = self._session.get(ProjectDBModel, str(project_id))
        return ProjectMapper.to_domain(db_model) if db_model else None

    def find_all(self) -> list[Project]:
        rows = self._session.query(ProjectDBModel).all()
        return [ProjectMapper.to_domain(row) for row in rows]

    def delete(self, project_id: UUID) -> None:
        db_model = self._session.get(ProjectDBModel, str(project_id))
        if db_model:
            self._session.delete(db_model)
            self._session.flush()
