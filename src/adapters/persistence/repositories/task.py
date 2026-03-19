from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.adapters.persistence.mappers.task import TaskMapper
from src.adapters.persistence.models.task import TaskDBModel
from src.domain.entities.task import Task
from src.domain.ports.task import TaskRepository, TaskSpecification


class SqlTaskRepository(TaskRepository):
    """
    SQLAlchemy implementation of the TaskRepository port.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, task: Task) -> Task:
        existing = self._session.get(TaskDBModel, str(task.id))
        if existing:
            TaskMapper.update_db_model(existing, task)
        else:
            self._session.add(TaskMapper.to_db_model(task))
        self._session.flush()
        return task

    def find_by_id(self, task_id: UUID) -> Optional[Task]:
        db_model = self._session.get(TaskDBModel, str(task_id))
        return TaskMapper.to_domain(db_model) if db_model else None

    def find_all(self, spec: Optional[TaskSpecification] = None) -> list[Task]:
        rows = self._session.query(TaskDBModel).all()
        tasks = [TaskMapper.to_domain(row) for row in rows]
        if spec:
            tasks = [t for t in tasks if spec.is_satisfied_by(t)]
        return tasks

    def count_open_by_project(self, project_id: UUID) -> int:
        return (
            self._session.query(TaskDBModel)
            .filter(
                TaskDBModel.project_id == str(project_id),
                TaskDBModel.completed == False,  # noqa: E712
            )
            .count()
        )

    def find_exceeding_deadline(
        self,
        project_id: UUID,
        deadline: datetime,
    ) -> list[Task]:
        rows = (
            self._session.query(TaskDBModel)
            .filter(
                TaskDBModel.project_id == str(project_id),
                TaskDBModel.deadline > deadline,
            )
            .all()
        )
        return [TaskMapper.to_domain(row) for row in rows]

    def delete(self, task_id: UUID) -> None:
        db_model = self._session.get(TaskDBModel, str(task_id))
        if db_model:
            self._session.delete(db_model)
            self._session.flush()
