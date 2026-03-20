from uuid import UUID

from fastapi import APIRouter, Depends

from src.adapters.api.dependencies import get_project_service, get_task_service
from src.adapters.api.v1.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from src.adapters.api.v1.schemas.task import TaskResponse
from src.application.dtos import CreateProjectDTO, UpdateProjectDTO
from src.application.project_service import ProjectService
from src.application.task_service import TaskService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=201,
    summary="Create a new project",
)
def create_project(
    body: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    dto = CreateProjectDTO(title=body.title, deadline=body.deadline)
    project = service.create_project(dto)
    return ProjectResponse.model_validate(project)


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List all projects",
)
def list_projects(
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    projects = service.get_all_projects()
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project by id",
)
def get_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = service.get_project(project_id)
    return ProjectResponse.model_validate(project)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project",
)
def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    dto = UpdateProjectDTO(title=body.title, deadline=body.deadline)
    project = service.update_project(project_id, dto)
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=204,
    summary="Delete a project",
)
def delete_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> None:
    service.delete_project(project_id)


@router.patch(
    "/{project_id}/complete",
    response_model=ProjectResponse,
    summary="Mark a project as completed",
)
def complete_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = service.complete_project(project_id)
    return ProjectResponse.model_validate(project)


@router.get(
    "/{project_id}/tasks",
    response_model=list[TaskResponse],
    summary="Get all tasks for a project",
)
def get_project_tasks(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> list[TaskResponse]:
    tasks = service.get_project_tasks(project_id)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.post(
    "/{project_id}/tasks/{task_id}/link",
    response_model=TaskResponse,
    summary="Link a task to a project",
)
def link_task(
    project_id: UUID,
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task = service.link_to_project(task_id, project_id)
    return TaskResponse.model_validate(task)


@router.delete(
    "/{project_id}/tasks/{task_id}/unlink",
    response_model=TaskResponse,
    summary="Unlink a task from a project",
)
def unlink_task(
    project_id: UUID,
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task = service.unlink_from_project(task_id)
    return TaskResponse.model_validate(task)
