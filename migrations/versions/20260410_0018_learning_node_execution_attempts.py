from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260410_0018"
down_revision = "20260410_0017"
branch_labels = None
depends_on = None


TABLE_NAME = "user_learning_node_execution_attempts"


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if _has_table(TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("learning_path_id", sa.String(length=128), sa.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("node_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("generation_reason", sa.String(length=64), nullable=False, server_default="on_start"),
        sa.Column("package_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("responses_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("result_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("context_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_node_window_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_user_learning_node_execution_attempts_user_id", TABLE_NAME, ["user_id"], unique=False)
    op.create_index("ix_user_learning_node_execution_attempts_learning_path_id", TABLE_NAME, ["learning_path_id"], unique=False)
    op.create_index("ix_user_learning_node_execution_attempts_node_id", TABLE_NAME, ["node_id"], unique=False)


def downgrade() -> None:
    if not _has_table(TABLE_NAME):
        return
    op.drop_index("ix_user_learning_node_execution_attempts_node_id", table_name=TABLE_NAME)
    op.drop_index("ix_user_learning_node_execution_attempts_learning_path_id", table_name=TABLE_NAME)
    op.drop_index("ix_user_learning_node_execution_attempts_user_id", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
