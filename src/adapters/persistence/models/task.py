from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database import Base

if TYPE_CHECKING:
    from src.adapters.persistence.models.project import ProjectDBModel


class TaskDBModel(Base):
    """
    Database model for the tasks table.
    """

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="UUID stored as string",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Must never exceed project deadline — enforced by domain",
    )
    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("projects.id", name="fk_tasks_project_id"),
        nullable=True,
        default=None,
        comment="Nullable — a task belongs to at most one project",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.current_timestamp(),
    )

    __table_args__ = (
        Index("idx_tasks_project_id", "project_id"),
        Index("idx_tasks_completed", "completed"),
        Index("idx_tasks_deadline", "deadline"),
    )

    project: Mapped[Optional["ProjectDBModel"]] = relationship(
        "ProjectDBModel",
        back_populates="tasks",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<TaskDBModel id={self.id!r} title={self.title!r} "
            f"completed={self.completed} project_id={self.project_id!r}>"
        )
