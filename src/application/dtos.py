from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class CreateProjectDTO:
    title: str
    deadline: datetime


@dataclass
class UpdateProjectDTO:
    title: Optional[str] = None
    deadline: Optional[datetime] = None


@dataclass
class CreateTaskDTO:
    title: str
    deadline: datetime
    description: Optional[str] = None
    project_id: Optional[UUID] = None


@dataclass
class UpdateTaskDTO:
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None