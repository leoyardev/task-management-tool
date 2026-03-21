from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database import Base

if TYPE_CHECKING:
    from src.adapters.persistence.models.task import TaskDBModel


class ProjectDBModel(Base):
    """
    Database model for the projects table.
    """

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="UUID stored as string",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
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

    tasks: Mapped[list["TaskDBModel"]] = relationship(
        "TaskDBModel",
        back_populates="project",
        lazy="select",
        # No cascade delete — task unlinking is handled by domain logic
        cascade="save-update, merge",
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectDBModel id={self.id!r} title={self.title!r} "
            f"completed={self.completed}>"
        )
