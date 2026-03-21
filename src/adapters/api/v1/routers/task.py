from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.adapters.api.dependencies import get_task_service
from src.adapters.api.v1.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from src.application.dtos import CreateTaskDTO, UpdateTaskDTO
from src.application.task_service import TaskService
from src.domain.ports.task import (
    BelongsToProjectSpec,
    CompletedTaskSpec,
    OpenTaskSpec,
    OverdueTaskSpec,
    TaskSpecification,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _build_spec(
    completed: Optional[bool],
    overdue: Optional[bool],
    project_id: Optional[UUID],
) -> Optional[TaskSpecification]:
    """
    Build a TaskSpecification from query parameters.
    Returns None if no filters are provided — find_all returns all tasks.
    """
    spec = None

    if completed is True:
        spec = CompletedTaskSpec()
    elif completed is False:
        spec = OpenTaskSpec()

    if overdue is True:
        overdue_spec = OverdueTaskSpec()
        spec = overdue_spec if spec is None else spec & overdue_spec

    if project_id is not None:
        project_spec = BelongsToProjectSpec(project_id)
        spec = project_spec if spec is None else spec & project_spec

    return spec


@router.get(
    "",
    response_model=list[TaskResponse],
    summary="List all tasks",
)
def list_tasks(
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    overdue: Optional[bool] = Query(None, description="Filter overdue tasks"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    service: TaskService = Depends(get_task_service),
) -> list[TaskResponse]:
    spec = _build_spec(completed, overdue, project_id)
    tasks = service.get_all_tasks(spec)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a task by id",
)
def get_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task = service.get_task(task_id)
    return TaskResponse.model_validate(task)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=201,
    summary="Create a new task",
)
def create_task(
    body: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    dto = CreateTaskDTO(
        title=body.title,
        deadline=body.deadline,
        description=body.description,
        project_id=body.project_id,
    )
    task = service.create_task(dto)
    return TaskResponse.model_validate(task)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
)
def update_task(
    task_id: UUID,
    body: TaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    dto = UpdateTaskDTO(
        title=body.title,
        description=body.description,
        deadline=body.deadline,
    )
    task = service.update_task(task_id, dto)
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=204,
    summary="Delete a task",
)
def delete_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> None:
    service.delete_task(task_id)


@router.patch(
    "/{task_id}/complete",
    response_model=TaskResponse,
    summary="Mark a task as completed",
)
def complete_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task = service.complete_task(task_id)
    return TaskResponse.model_validate(task)
