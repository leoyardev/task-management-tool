"""create task table

Revision ID: 478f257a1689
Revises: e797093f112e
Create Date: 2026-03-19 16:37:39.152819

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "478f257a1689"
down_revision: Union[str, Sequence[str], None] = "e797093f112e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            nullable=False,
            comment="UUID stored as string",
        ),
        sa.Column(
            "title",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
        ),
        sa.Column(
            "deadline",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Must never exceed project deadline — enforced by domain",
        ),
        sa.Column(
            "completed",
            sa.Boolean,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", name="fk_tasks_project_id"),
            nullable=True,
            comment="Nullable — a task belongs to at most one project",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_index("idx_tasks_project_id", "tasks", ["project_id"])
    op.create_index("idx_tasks_completed", "tasks", ["completed"])
    op.create_index("idx_tasks_deadline", "tasks", ["deadline"])


def downgrade() -> None:
    op.drop_index("idx_tasks_deadline", table_name="tasks")
    op.drop_index("idx_tasks_completed", table_name="tasks")
    op.drop_index("idx_tasks_project_id", table_name="tasks")
    op.drop_table("tasks")
