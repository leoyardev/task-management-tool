from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    deadline: datetime


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    deadline: datetime
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    deadline: Optional[datetime] = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ProjectUpdate":
        if self.title is None and self.deadline is None:
            raise ValueError("At least one field must be provided.")
        return self
