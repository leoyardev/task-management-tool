from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    deadline: datetime
    description: Optional[str] = None
    project_id: Optional[UUID] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    deadline: Optional[datetime] = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "TaskUpdate":
        if self.title is None and self.description is None and self.deadline is None:
            raise ValueError("At least one field must be provided.")
        return self


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    deadline: datetime
    completed: bool
    project_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskFiltersQuery(BaseModel):
    """
    Query parameters for GET /tasks.
    Used to build a TaskSpecification in the router.
    """

    completed: Optional[bool] = None
    overdue: Optional[bool] = None
    project_id: Optional[UUID] = None
