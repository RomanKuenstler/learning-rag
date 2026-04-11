from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260410_0017"
down_revision = "20260410_0016"
branch_labels = None
depends_on = None


TABLE_NAME = "user_learning_node_contexts"


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if _has_table(TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("learning_path_id", sa.String(length=128), sa.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("node_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("generation_reason", sa.String(length=64), nullable=False, server_default="on_demand"),
        sa.Column("context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("course_context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("chapter_branch_context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("prior_node_context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("target_node_context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("next_node_context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("ksa_context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("readiness_context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("derived_assumptions_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_hash", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "learning_path_id", "node_id", name="uq_user_learning_node_contexts_user_path_node"),
    )
    op.create_index("ix_user_learning_node_contexts_user_id", TABLE_NAME, ["user_id"], unique=False)
    op.create_index("ix_user_learning_node_contexts_learning_path_id", TABLE_NAME, ["learning_path_id"], unique=False)
    op.create_index("ix_user_learning_node_contexts_node_id", TABLE_NAME, ["node_id"], unique=False)


def downgrade() -> None:
    if not _has_table(TABLE_NAME):
        return
    op.drop_index("ix_user_learning_node_contexts_node_id", table_name=TABLE_NAME)
    op.drop_index("ix_user_learning_node_contexts_learning_path_id", table_name=TABLE_NAME)
    op.drop_index("ix_user_learning_node_contexts_user_id", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
