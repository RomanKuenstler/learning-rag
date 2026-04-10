from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260408_0014"
down_revision = "20260408_0013"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if _has_table("learning_paths"):
        if not _has_column("learning_paths", "schema_version"):
            op.add_column(
                "learning_paths",
                sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
            )
        if not _has_column("learning_paths", "skilltree_definition"):
            op.add_column(
                "learning_paths",
                sa.Column("skilltree_definition", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            )

    if not _has_table("user_learning_node_progress"):
        op.create_table(
            "user_learning_node_progress",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "learning_path_id",
                sa.String(length=128),
                sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("node_id", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "user_id",
                "learning_path_id",
                "node_id",
                name="uq_user_learning_node_progress_user_path_node",
            ),
        )
        op.create_index("ix_user_learning_node_progress_user_id", "user_learning_node_progress", ["user_id"])
        op.create_index("ix_user_learning_node_progress_learning_path_id", "user_learning_node_progress", ["learning_path_id"])


def downgrade() -> None:
    if _has_table("user_learning_node_progress"):
        op.drop_table("user_learning_node_progress")

    if _has_table("learning_paths") and _has_column("learning_paths", "skilltree_definition"):
        with op.batch_alter_table("learning_paths") as batch_op:
            batch_op.drop_column("skilltree_definition")
    if _has_table("learning_paths") and _has_column("learning_paths", "schema_version"):
        with op.batch_alter_table("learning_paths") as batch_op:
            batch_op.drop_column("schema_version")
