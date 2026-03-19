from uuid import UUID

from src.adapters.persistence.mappers.utils import ensure_utc
from src.adapters.persistence.models.task import TaskDBModel
from src.domain.entities.task import Task


class TaskMapper:
    """
    Converts between TaskDBModel (persistence) and Task (domain).
    """

    @staticmethod
    def to_domain(db_model: TaskDBModel) -> Task:
        """
        DB row → domain entity.
        Called after every SELECT.
        """
        return Task(
            id=UUID(db_model.id),
            title=db_model.title,
            description=db_model.description,
            deadline=ensure_utc(db_model.deadline),
            completed=db_model.completed,
            project_id=UUID(db_model.project_id) if db_model.project_id else None,
            created_at=ensure_utc(db_model.created_at),
            updated_at=ensure_utc(db_model.updated_at),
        )

    @staticmethod
    def to_db_model(task: Task) -> TaskDBModel:
        """
        Domain entity → new DB row.
        Called on INSERT.
        """
        return TaskDBModel(
            id=str(task.id),
            title=task.title,
            description=task.description,
            deadline=task.deadline,
            completed=task.completed,
            project_id=str(task.project_id) if task.project_id else None,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    def update_db_model(db_model: TaskDBModel, task: Task) -> TaskDBModel:
        """
        Apply domain entity state onto an existing DB row.
        Called on UPDATE — mutates the already-tracked row so
        SQLAlchemy issues UPDATE not DELETE + INSERT.
        id and created_at excluded — immutable once set.
        """
        db_model.title = task.title
        db_model.description = task.description
        db_model.deadline = task.deadline
        db_model.completed = task.completed
        db_model.project_id = str(task.project_id) if task.project_id else None
        db_model.updated_at = task.updated_at
        return db_model
