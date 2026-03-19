from typing import Optional
from uuid import UUID

from src.application.dtos import CreateTaskDTO, UpdateTaskDTO
from src.domain.events.events import TaskReopened
from src.domain.exceptions.exceptions import NotFoundError
from src.domain.entities.task import Task
from src.domain.ports.notification import NotificationPort
from src.domain.ports.project import ProjectRepository
from src.domain.ports.task import TaskRepository, TaskSpecification


class TaskService:
    """
    Orchestrates all task use cases.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        notification: NotificationPort,
        auto_complete_project: bool = False,
    ) -> None:
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._notification = notification
        self._auto_complete_project = auto_complete_project


    def get_task(self, task_id: UUID) -> Task:
        task = self._task_repo.find_by_id(task_id)
        if not task:
            raise NotFoundError("Task", str(task_id))
        return task

    def get_all_tasks(self, spec: Optional[TaskSpecification] = None) -> list[Task]:
        return self._task_repo.find_all(spec)


    def create_task(self, dto: CreateTaskDTO) -> Task:
        project_deadline = None
        if dto.project_id:
            project = self._project_repo.find_by_id(dto.project_id)
            if not project:
                raise NotFoundError("Project", str(dto.project_id))
            project_deadline = project.deadline

        task = Task.create(
            title=dto.title,
            deadline=dto.deadline,
            description=dto.description,
            project_id=dto.project_id,
            project_deadline=project_deadline,
        )
        saved = self._task_repo.save(task)
        self._dispatch(task.pull_events())
        return saved

    def update_task(self, task_id: UUID, dto: UpdateTaskDTO) -> Task:
        task = self.get_task(task_id)
        task.update(
            title=dto.title,
            description=dto.description,
            deadline=dto.deadline,
        )
        return self._task_repo.save(task)

    def delete_task(self, task_id: UUID) -> None:
        self.get_task(task_id)
        self._task_repo.delete(task_id)

    def complete_task(self, task_id: UUID) -> Task:
        task = self.get_task(task_id)
        task.mark_complete()
        saved = self._task_repo.save(task)
        self._dispatch(task.pull_events())
        self._handle_auto_complete(task)
        return saved

    def reopen_task(self, task_id: UUID) -> Task:
        task = self.get_task(task_id)
        task.reopen()
        saved = self._task_repo.save(task)
        self._handle_project_reopen(task)
        return saved

    def link_to_project(self, task_id: UUID, project_id: UUID) -> Task:
        task = self.get_task(task_id)
        project = self._project_repo.find_by_id(project_id)
        if not project:
            raise NotFoundError("Project", str(project_id))
        task.link_to_project(project_id, project.deadline)
        return self._task_repo.save(task)

    def unlink_from_project(self, task_id: UUID) -> Task:
        task = self.get_task(task_id)
        task.unlink_from_project()
        return self._task_repo.save(task)


    def _handle_auto_complete(self, task: Task) -> None:
        """
        When auto_complete_project is enabled and the last open task
        in a project is completed, automatically complete the project.
        """
        if not self._auto_complete_project or not task.project_id:
            return
        open_count = self._task_repo.count_open_by_project(task.project_id)
        if open_count == 0:
            project = self._project_repo.find_by_id(task.project_id)
            if project and not project.completed:
                project.mark_complete(open_task_count=0)
                self._project_repo.save(project)
                self._dispatch(project.pull_events())

    def _handle_project_reopen(self, task: Task) -> None:
        """
        When a task is reopened inside a completed project,
        automatically reopen the project — spec requirement.
        """
        for event in task.pull_events():
            if isinstance(event, TaskReopened) and event.project_id:
                project = self._project_repo.find_by_id(event.project_id)
                if project and project.completed:
                    project.reopen()
                    self._project_repo.save(project)
            self._notification.notify(event)

    def _dispatch(self, events) -> None:
        for event in events:
            self._notification.notify(event)