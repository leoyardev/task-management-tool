from uuid import UUID

from src.application.dtos import CreateProjectDTO, UpdateProjectDTO
from src.domain.events.events import ProjectDeadlineChanged
from src.domain.exceptions.exceptions import NotFoundError
from src.domain.entities.project import Project
from src.domain.ports.notification import NotificationPort
from src.domain.ports.project import ProjectRepository
from src.domain.ports.task import TaskRepository, BelongsToProjectSpec


class ProjectService:
    """
    Orchestrates all project use cases.
    """

    def __init__(
        self,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        notification: NotificationPort,
    ) -> None:
        self._project_repo = project_repo
        self._task_repo = task_repo
        self._notification = notification

    def get_project(self, project_id: UUID) -> Project:
        project = self._project_repo.find_by_id(project_id)
        if not project:
            raise NotFoundError("Project", str(project_id))
        return project

    def get_all_projects(self) -> list[Project]:
        return self._project_repo.find_all()

    def get_project_tasks(self, project_id: UUID):
        self.get_project(project_id)  # raises NotFoundError if missing
        return self._task_repo.find_all(BelongsToProjectSpec(project_id))


    def create_project(self, dto: CreateProjectDTO) -> Project:
        project = Project.create(
            title=dto.title,
            deadline=dto.deadline,
        )
        return self._project_repo.save(project)

    def update_project(self, project_id: UUID, dto: UpdateProjectDTO) -> Project:
        project = self.get_project(project_id)
        project.update(title=dto.title, deadline=dto.deadline)

        for event in project.pull_events():
            if isinstance(event, ProjectDeadlineChanged):
                self._cascade_deadline(project_id, event.new_deadline)
            self._notification.notify(event)

        return self._project_repo.save(project)

    def delete_project(self, project_id: UUID) -> None:
        self.get_project(project_id)  # raises NotFoundError if missing
        self._project_repo.delete(project_id)

    def complete_project(self, project_id: UUID) -> Project:
        project = self.get_project(project_id)
        open_count = self._task_repo.count_open_by_project(project_id)
        project.mark_complete(open_count)
        saved = self._project_repo.save(project)
        self._dispatch(project.pull_events())
        return saved


    def _cascade_deadline(self, project_id: UUID, new_deadline) -> None:
        """
        When a project deadline moves earlier, find all tasks whose
        deadline now exceeds it and clamp them to the new deadline.
        """
        affected = self._task_repo.find_exceeding_deadline(
            project_id,
            new_deadline,
        )
        for task in affected:
            task.deadline = new_deadline
            task.project_deadline = new_deadline
            self._task_repo.save(task)

    def _dispatch(self, events) -> None:
        for event in events:
            self._notification.notify(event)