from uuid import UUID

from src.adapters.persistence.mappers.utils import ensure_utc
from src.adapters.persistence.models.project import ProjectDBModel
from src.domain.entities.project import Project


class ProjectMapper:
    """
    Converts between ProjectDBModel (persistence) and Project (domain).
    """

    @staticmethod
    def to_domain(db_model: ProjectDBModel) -> Project:
        """
        DB row → domain entity.
        Called after every SELECT.
        """
        return Project(
            id=UUID(db_model.id),
            title=db_model.title,
            deadline=ensure_utc(db_model.deadline),
            completed=db_model.completed,
            created_at=ensure_utc(db_model.created_at),
            updated_at=ensure_utc(db_model.updated_at),
        )

    @staticmethod
    def to_db_model(project: Project) -> ProjectDBModel:
        """
        Domain entity → new DB row.
        Called on INSERT.
        """
        return ProjectDBModel(
            id=str(project.id),
            title=project.title,
            deadline=project.deadline,
            completed=project.completed,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    @staticmethod
    def update_db_model(db_model: ProjectDBModel, project: Project) -> ProjectDBModel:
        """
        Apply domain entity state onto an existing DB row.
        Called on UPDATE — mutates the already-tracked row so
        SQLAlchemy issues UPDATE not DELETE + INSERT.
        id and created_at excluded — immutable once set.
        """
        db_model.title = project.title
        db_model.deadline = project.deadline
        db_model.completed = project.completed
        db_model.updated_at = project.updated_at
        return db_model
